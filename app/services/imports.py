import logging
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile, ZipInfo

from docx import Document

from app.core.config import get_settings
from app.db.session import async_session
from app.models import ImportBatch, ImportItem, TextDocument, utc_now
from app.services.documents import create_text_document


logger = logging.getLogger(__name__)

BATCH_PENDING = 'pending'
BATCH_PROCESSING = 'processing'
BATCH_COMPLETED = 'completed'
BATCH_COMPLETED_WITH_ERRORS = 'completed_with_errors'
BATCH_FAILED = 'failed'

ITEM_PENDING = 'pending'
ITEM_PROCESSED = 'processed'
ITEM_FAILED = 'failed'


class ImportFileError(Exception):
    pass


def is_safe_zip_path(filename: str) -> bool:
    path = PurePosixPath(filename)
    return not (
        path.is_absolute()
        or any(part in {'', '.', '..'} for part in path.parts)
    )


def read_txt(data: bytes) -> str:
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        raise ImportFileError('Invalid UTF-8 text file.') from None


def read_docx(data: bytes) -> str:
    try:
        document = Document(BytesIO(data))
    except Exception:
        raise ImportFileError('Invalid DOCX file.') from None

    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    return '\n\n'.join(paragraphs)


def read_document(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == '.txt':
        return read_txt(data)
    if suffix == '.docx':
        return read_docx(data)
    raise ImportFileError('Unsupported file extension.')


async def process_import_batch(import_id: int) -> None:
    settings = get_settings()
    async with async_session() as db:
        batch = await db.get(ImportBatch, import_id)
        if batch is None:
            logger.error('Import batch %s was not found', import_id)
            return

        batch.status = BATCH_PROCESSING
        batch.started_at = utc_now()
        await db.commit()
        archive_path = Path(batch.archive_path)

    try:
        if archive_path.stat().st_size > settings.max_archive_size:
            await mark_batch_failed(import_id, 'Archive is too large.')
            return

        with ZipFile(archive_path) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            if not infos:
                await mark_batch_failed(
                    import_id,
                    'Archive does not contain files.',
                )
                return
            if len(infos) > settings.max_archive_files:
                await mark_batch_failed(
                    import_id,
                    'Archive contains too many files.',
                )
                return
            if any(not is_safe_zip_path(info.filename) for info in infos):
                await mark_batch_failed(
                    import_id,
                    'Archive contains unsafe paths.',
                )
                return

            items = await create_import_items(import_id, infos)

            for item_id, info in items:
                await process_import_item(item_id, archive, info)

            await finish_import_batch(import_id)
    except (FileNotFoundError, BadZipFile):
        await mark_batch_failed(import_id, 'Invalid ZIP archive.')
    except Exception as error:
        logger.exception('Import batch %s failed', import_id)
        await mark_batch_failed(import_id, 'Import failed.')
        raise error
    finally:
        archive_path.unlink(missing_ok=True)


async def mark_batch_failed(import_id: int, error: str) -> None:
    logger.warning('Import batch %s failed: %s', import_id, error)
    async with async_session() as db:
        batch = await db.get(ImportBatch, import_id)
        if batch is None:
            return
        batch.status = BATCH_FAILED
        batch.finished_at = utc_now()
        batch.error = error
        await db.commit()


async def create_import_items(
    import_id: int,
    infos: list[ZipInfo],
) -> list[tuple[int, ZipInfo]]:
    items = []
    async with async_session() as db:
        for info in infos:
            item = ImportItem(
                import_batch_id=import_id,
                filename=info.filename,
                status=ITEM_PENDING,
                error='',
            )
            db.add(item)
            await db.flush()
            items.append((item.id, info))
        batch = await db.get(ImportBatch, import_id)
        if batch is not None:
            batch.files_total = len(infos)
        await db.commit()
    return items


async def process_import_item(
    item_id: int,
    archive: ZipFile,
    info: ZipInfo,
) -> None:
    settings = get_settings()
    async with async_session() as db:
        item = await db.get(ImportItem, item_id)
        batch = None
        if item is not None:
            batch = await db.get(ImportBatch, item.import_batch_id)
        if item is None or batch is None:
            return

        try:
            document = await create_document_from_zip_item(
                db,
                batch.user_id,
                archive,
                info,
                settings.max_document_size,
            )
        except ImportFileError as error:
            item.status = ITEM_FAILED
            item.error = str(error)
            batch.files_failed += 1
        else:
            item.status = ITEM_PROCESSED
            item.document_id = document.id
            batch.files_processed += 1

        await db.commit()


async def create_document_from_zip_item(
    db,
    user_id: int,
    archive: ZipFile,
    info: ZipInfo,
    max_document_size: int,
) -> TextDocument:
    document_extensions = get_settings().document_extensions
    if Path(info.filename).suffix.lower() not in document_extensions:
        raise ImportFileError('Unsupported file extension.')
    if info.file_size > max_document_size:
        raise ImportFileError('Document is too large.')

    data = archive.read(info)
    if len(data) > max_document_size:
        raise ImportFileError('Document is too large.')

    content = read_document(info.filename, data)
    if not content.strip():
        raise ImportFileError('Document is empty.')

    original_filename = PurePosixPath(info.filename).name
    if len(original_filename) > 255:
        raise ImportFileError('Filename is too long.')

    document = await create_text_document(
        db,
        user_id,
        Path(original_filename).stem,
        original_filename,
        content,
    )
    await db.flush()
    return document


async def finish_import_batch(import_id: int) -> None:
    async with async_session() as db:
        batch = await db.get(ImportBatch, import_id)
        if batch is None:
            return

        if batch.files_failed:
            batch.status = BATCH_COMPLETED_WITH_ERRORS
        else:
            batch.status = BATCH_COMPLETED
        batch.finished_at = utc_now()
        await db.commit()

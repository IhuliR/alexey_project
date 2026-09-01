import json
import logging
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import async_session
from app.models import Annotation, ExportJob, Label, TextDocument, utc_now


logger = logging.getLogger(__name__)

EXPORT_PENDING = 'pending'
EXPORT_PROCESSING = 'processing'
EXPORT_COMPLETED = 'completed'
EXPORT_FAILED = 'failed'

EXPORT_JSON = 'json'
SUPPORTED_EXPORT_FORMATS = {EXPORT_JSON}


class ExportError(Exception):
    pass


def format_exported_at() -> str:
    return utc_now().isoformat().replace('+00:00', 'Z')


def serialize_datetime(value) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace('+00:00', 'Z')


def get_export_download_filename(
    document: TextDocument | None,
    document_id: int | None,
    export_format: str,
) -> str:
    if document is not None and document.slug:
        return f'{document.slug}_export.{export_format}'
    if document_id is not None:
        return f'document_{document_id}_export.{export_format}'
    return f'document_export.{export_format}'


def build_document_export(
    document: TextDocument,
    labels: list[Label],
    annotations: list[Annotation],
) -> dict:
    labels_payload = [
        {
            'id': label.id,
            'name': label.name,
            'color': label.color,
        }
        for label in labels
    ]
    labels_by_id = {
        label['id']: label
        for label in labels_payload
    }

    return {
        'schema_version': 2,
        'exported_at': format_exported_at(),
        'document': {
            'id': document.id,
            'title': document.title,
            'slug': document.slug,
            'original_filename': document.original_filename,
            'created_at': serialize_datetime(document.created_at),
            'content': document.content,
        },
        'labels': labels_payload,
        'annotations': [
            {
                'id': annotation.id,
                'start': annotation.start,
                'end': annotation.end,
                'text': document.content[annotation.start:annotation.end],
                'label': labels_by_id.get(annotation.label_id),
                'label_id': annotation.label_id,
                'created_at': serialize_datetime(annotation.created_at),
            }
            for annotation in annotations
        ],
    }


def write_json_export(payload: dict, path: Path) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


async def process_export_job(export_id: int) -> None:
    async with async_session() as db:
        job = await db.get(ExportJob, export_id)
        if job is None:
            logger.error('Export job %s was not found', export_id)
            return

        job.status = EXPORT_PROCESSING
        job.started_at = utc_now()
        await db.commit()

    try:
        file_path = await generate_export_file(export_id)
    except ExportError as error:
        await mark_export_failed(export_id, str(error))
    except Exception as error:
        logger.exception('Export job %s failed', export_id)
        await mark_export_failed(export_id, 'Export failed.')
        raise error
    else:
        async with async_session() as db:
            job = await db.get(ExportJob, export_id)
            if job is None:
                return
            job.status = EXPORT_COMPLETED
            job.file_path = str(file_path)
            job.finished_at = utc_now()
            job.error = ''
            await db.commit()


async def generate_export_file(export_id: int) -> Path:
    settings = get_settings()
    async with async_session() as db:
        job = await db.get(ExportJob, export_id)
        if job is None:
            raise ExportError('Export job was not found.')
        if job.format not in SUPPORTED_EXPORT_FORMATS:
            raise ExportError('Unsupported export format.')
        if job.document_id is None:
            raise ExportError('Document was not found.')

        document = await db.scalar(
            select(TextDocument).where(
                TextDocument.id == job.document_id,
                TextDocument.user_id == job.user_id,
            )
        )
        if document is None:
            raise ExportError('Document was not found.')

        labels = list(
            (
                await db.scalars(
                    select(Label)
                    .where(Label.user_id == job.user_id)
                    .order_by(Label.id)
                )
            ).all()
        )
        annotations = list(
            (
                await db.scalars(
                    select(Annotation)
                    .where(Annotation.document_id == document.id)
                    .order_by(Annotation.id)
                )
            ).all()
        )

        payload = build_document_export(document, labels, annotations)

    export_path = settings.export_storage_dir / f'{export_id}-{uuid4()}.json'
    export_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_json_export(payload, export_path)
    except Exception:
        export_path.unlink(missing_ok=True)
        raise
    return export_path


async def mark_export_failed(export_id: int, error: str) -> None:
    async with async_session() as db:
        job = await db.get(ExportJob, export_id)
        if job is None:
            return
        if job.file_path:
            Path(job.file_path).unlink(missing_ok=True)
            job.file_path = ''
        job.status = EXPORT_FAILED
        job.finished_at = utc_now()
        job.error = error
        await db.commit()

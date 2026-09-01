from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from kombu.exceptions import KombuError
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import get_settings
from app.models import ImportBatch, ImportItem, utc_now
from app.schemas import ImportBatchRead, ImportItemRead
from app.services.imports import BATCH_FAILED, BATCH_PENDING
from app.tasks.imports import process_import


router = APIRouter(prefix='/api/v1/imports', tags=['Imports'])
QUEUE_ERROR_MESSAGE = (
    'Не удалось поставить импорт '
    'в очередь.'
)


async def get_import_batch(
    import_id: int,
    user: CurrentUser,
    db: DatabaseSession,
) -> ImportBatch:
    batch = await db.scalar(
        select(ImportBatch).where(
            ImportBatch.id == import_id,
            ImportBatch.user_id == user.id,
        )
    )
    if batch is None:
        raise HTTPException(status_code=404, detail='Not found.')
    return batch


async def save_archive(file: UploadFile, archive_path: Path) -> None:
    settings = get_settings()
    size = 0
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    with archive_path.open('wb') as saved_file:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_archive_size:
                archive_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail='Archive is too large.',
                )
            saved_file.write(chunk)


@router.post(
    '/',
    response_model=ImportBatchRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_import(
    user: CurrentUser,
    db: DatabaseSession,
    file: Annotated[UploadFile | None, File()] = None,
) -> ImportBatch:
    if file is None:
        raise HTTPException(
            status_code=400,
            detail='Файл не найден.',
        )
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail='Только .zip файлы разрешены.',
        )

    settings = get_settings()
    archive_path = settings.import_storage_dir / f'{uuid4()}.zip'
    await save_archive(file, archive_path)

    batch = ImportBatch(
        user_id=user.id,
        status=BATCH_PENDING,
        files_total=0,
        files_processed=0,
        files_failed=0,
        archive_path=str(archive_path),
        created_at=utc_now(),
        error='',
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    try:
        process_import.apply_async(
            args=(batch.id,),
            queue='imports',
            routing_key='imports',
        )
    except (KombuError, OSError):
        batch.status = BATCH_FAILED
        batch.finished_at = utc_now()
        batch.error = 'Could not enqueue import task.'
        await db.commit()
        await db.refresh(batch)
        archive_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=503,
            detail=QUEUE_ERROR_MESSAGE,
        ) from None

    return batch


@router.get('/{import_id}/', response_model=ImportBatchRead)
async def retrieve_import(
    batch: Annotated[ImportBatch, Depends(get_import_batch)],
) -> ImportBatch:
    return batch


@router.get('/{import_id}/items/', response_model=list[ImportItemRead])
async def list_import_items(
    batch: Annotated[ImportBatch, Depends(get_import_batch)],
    db: DatabaseSession,
) -> list[ImportItem]:
    return list(
        (
            await db.scalars(
                select(ImportItem)
                .where(ImportItem.import_batch_id == batch.id)
                .order_by(ImportItem.id)
            )
        ).all()
    )

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from kombu.exceptions import KombuError
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.errors import ApiValidationError
from app.models import ExportJob, TextDocument, utc_now
from app.schemas import ExportJobCreate, ExportJobRead
from app.services.exports import (
    EXPORT_COMPLETED,
    EXPORT_FAILED,
    EXPORT_JSON,
    EXPORT_PENDING,
    SUPPORTED_EXPORT_FORMATS,
    get_export_download_filename,
)
from app.tasks.exports import generate_export


router = APIRouter(prefix='/api/v1/exports', tags=['Exports'])
QUEUE_ERROR_MESSAGE = (
    'Не удалось поставить экспорт '
    'в очередь.'
)


async def get_export_job(
    export_id: int,
    user: CurrentUser,
    db: DatabaseSession,
) -> ExportJob:
    job = await db.scalar(
        select(ExportJob).where(
            ExportJob.id == export_id,
            ExportJob.user_id == user.id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail='Not found.')
    return job


async def get_owned_document(
    document_id: int,
    user: CurrentUser,
    db: DatabaseSession,
) -> TextDocument:
    document = await db.scalar(
        select(TextDocument).where(
            TextDocument.id == document_id,
            TextDocument.user_id == user.id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail='Not found.')
    return document


@router.post(
    '/',
    response_model=ExportJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_export(
    data: ExportJobCreate,
    user: CurrentUser,
    db: DatabaseSession,
) -> ExportJob:
    export_format = data.format.lower()
    if export_format not in SUPPORTED_EXPORT_FORMATS:
        raise ApiValidationError({'format': 'Unsupported export format.'})

    await get_owned_document(data.document_id, user, db)

    job = ExportJob(
        user_id=user.id,
        document_id=data.document_id,
        format=export_format,
        status=EXPORT_PENDING,
        file_path='',
        created_at=utc_now(),
        error='',
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    try:
        generate_export.apply_async(
            args=(job.id,),
            queue='exports',
            routing_key='exports',
        )
    except (KombuError, OSError):
        job.status = EXPORT_FAILED
        job.finished_at = utc_now()
        job.error = 'Could not enqueue export task.'
        await db.commit()
        await db.refresh(job)
        raise HTTPException(
            status_code=503,
            detail=QUEUE_ERROR_MESSAGE,
        ) from None

    return job


@router.get('/{export_id}/', response_model=ExportJobRead)
async def retrieve_export(
    job: Annotated[ExportJob, Depends(get_export_job)],
) -> ExportJob:
    return job


@router.get('/{export_id}/download/')
async def download_export(
    job: Annotated[ExportJob, Depends(get_export_job)],
    user: CurrentUser,
    db: DatabaseSession,
) -> FileResponse:
    if job.status != EXPORT_COMPLETED or not job.file_path:
        raise HTTPException(status_code=409, detail='Export is not ready.')

    path = Path(job.file_path)
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail='Export file was not found.',
        )

    document = None
    if job.document_id is not None:
        document = await get_owned_document(job.document_id, user, db)

    filename = get_export_download_filename(
        document,
        job.document_id,
        job.format or EXPORT_JSON,
    )
    return FileResponse(
        path,
        media_type='application/json',
        filename=filename,
    )

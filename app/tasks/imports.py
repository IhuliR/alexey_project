import asyncio

from app.services.imports import process_import_batch
from app.tasks.celery_app import celery_app


@celery_app.task(name='app.tasks.imports.process_import')
def process_import(import_id: int) -> None:
    asyncio.run(process_import_batch(import_id))

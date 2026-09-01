import asyncio

from app.db.session import close_db
from app.services.imports import process_import_batch
from app.tasks.celery_app import celery_app


async def run_import(import_id: int) -> None:
    try:
        await process_import_batch(import_id)
    finally:
        await close_db()


@celery_app.task(name='app.tasks.imports.process_import')
def process_import(import_id: int) -> None:
    asyncio.run(run_import(import_id))

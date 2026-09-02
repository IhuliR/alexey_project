import asyncio

from app.db.session import close_db
from app.services.exports import process_export_job
from app.tasks.celery_app import celery_app


async def run_export(export_id: int) -> None:
    try:
        await process_export_job(export_id)
    finally:
        await close_db()


@celery_app.task(name='app.tasks.exports.generate_export')
def generate_export(export_id: int) -> None:
    asyncio.run(run_export(export_id))

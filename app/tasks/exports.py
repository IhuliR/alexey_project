import asyncio

from app.services.exports import process_export_job
from app.tasks.celery_app import celery_app


@celery_app.task(name='app.tasks.exports.generate_export')
def generate_export(export_id: int) -> None:
    asyncio.run(process_export_job(export_id))

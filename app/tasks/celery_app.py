import logging

from celery import Celery, signals
from kombu import Queue

from app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    'formaslov',
    broker=settings.celery_broker_url,
    include=[
        'app.tasks.imports',
        'app.tasks.exports',
    ],
)

celery_app.conf.update(
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    task_ignore_result=True,
    task_queues=(
        Queue('imports', routing_key='imports'),
        Queue('exports', routing_key='exports'),
    ),
    task_routes={
        'app.tasks.imports.*': {
            'queue': 'imports',
            'routing_key': 'imports',
        },
        'app.tasks.exports.*': {
            'queue': 'exports',
            'routing_key': 'exports',
        },
    },
)


@signals.worker_ready.connect
def log_worker_ready(sender: object, **kwargs: object) -> None:
    logger.info('Celery worker is ready: %s', sender)


@signals.task_failure.connect
def log_task_failure(
    task_id: str,
    exception: BaseException,
    sender: object | None = None,
    **kwargs: object,
) -> None:
    logger.error(
        'Celery task failed: task=%s task_id=%s error=%s',
        sender,
        task_id,
        exception,
    )

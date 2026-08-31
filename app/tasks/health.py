import logging

from app.tasks.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(name='app.tasks.health.healthcheck')
def healthcheck(message: str = 'ok') -> str:
    logger.info('Celery healthcheck task executed: %s', message)
    return message

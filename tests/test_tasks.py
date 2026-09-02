import asyncio

import pytest

from app.tasks import exports as export_tasks
from app.tasks import imports as import_tasks
from app.core.config import Settings, get_settings
from app.tasks.celery_app import celery_app
from app.tasks.exports import generate_export
from app.tasks.imports import process_import


def test_celery_app_uses_configured_broker_url() -> None:
    assert celery_app.conf.broker_url == get_settings().celery_broker_url


def test_settings_read_celery_broker_url_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker_url = 'amqp://guest:guest@example:5672//'
    monkeypatch.setenv('CELERY_BROKER_URL', broker_url)

    settings = Settings(
        secret_key='test-secret-key-for-formaslov-fastapi-tests',
        _env_file=None,
    )

    assert settings.celery_broker_url == broker_url


def test_settings_read_import_limits_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('MAX_ARCHIVE_SIZE', '1024')
    monkeypatch.setenv('MAX_ARCHIVE_FILES', '2')
    monkeypatch.setenv('MAX_DOCUMENT_SIZE', '512')
    monkeypatch.setenv('ALLOWED_DOCUMENT_EXTENSIONS', '.txt,.docx')
    monkeypatch.setenv('EXPORT_STORAGE_DIR', '/tmp/exports')

    settings = Settings(
        secret_key='test-secret-key-for-formaslov-fastapi-tests',
        _env_file=None,
    )

    assert settings.max_archive_size == 1024
    assert settings.max_archive_files == 2
    assert settings.max_document_size == 512
    assert settings.document_extensions == {'.txt', '.docx'}
    assert str(settings.export_storage_dir) == '/tmp/exports'


def test_process_import_task_is_registered() -> None:
    assert 'app.tasks.imports.process_import' in celery_app.tasks


def test_generate_export_task_is_registered() -> None:
    assert 'app.tasks.exports.generate_export' in celery_app.tasks


def test_celery_queues_and_routes_are_configured() -> None:
    queue_names = {queue.name for queue in celery_app.conf.task_queues}
    assert queue_names == {'imports', 'exports'}

    routes = celery_app.conf.task_routes
    assert routes['app.tasks.imports.*']['queue'] == 'imports'
    assert routes['app.tasks.imports.*']['routing_key'] == 'imports'
    assert routes['app.tasks.exports.*']['queue'] == 'exports'
    assert routes['app.tasks.exports.*']['routing_key'] == 'exports'


def test_process_import_task_uses_imports_route() -> None:
    route = celery_app.amqp.router.route(
        {},
        process_import.name,
        args=(1,),
        kwargs={},
    )
    assert route['queue'].name == 'imports'
    assert route['routing_key'] == 'imports'


def test_generate_export_task_uses_exports_route() -> None:
    route = celery_app.amqp.router.route(
        {},
        generate_export.name,
        args=(1,),
        kwargs={},
    )
    assert route['queue'].name == 'exports'
    assert route['routing_key'] == 'exports'


@pytest.mark.parametrize(
    ('task_module', 'run_task', 'service_name'),
    [
        (import_tasks, import_tasks.run_import, 'process_import_batch'),
        (export_tasks, export_tasks.run_export, 'process_export_job'),
    ],
)
def test_background_tasks_close_database_engine(
    monkeypatch: pytest.MonkeyPatch,
    task_module,
    run_task,
    service_name: str,
) -> None:
    calls = []

    async def process(job_id: int) -> None:
        calls.append(('process', job_id))

    async def close() -> None:
        calls.append(('close', None))

    monkeypatch.setattr(task_module, service_name, process)
    monkeypatch.setattr(task_module, 'close_db', close)

    asyncio.run(run_task(7))

    assert calls == [('process', 7), ('close', None)]

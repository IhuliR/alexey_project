import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.routers import exports as exports_router
from app.core.config import get_settings
from app.db.session import async_session, close_db
from app.main import app
from app.models import ExportJob, utc_now
from app.services.exports import (
    EXPORT_PENDING,
    process_export_job,
)
from tests.test_api import (
    TEST_DATABASE_URL,
    auth_headers,
    clean_database,
    clean_labels_cache,
    create_document,
    create_label,
    register_and_login,
)


pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason='TEST_DATABASE_URL is not configured',
)


@pytest.fixture(autouse=True)
def empty_database() -> None:
    clean_labels_cache()
    clean_database()
    yield
    clean_database()
    clean_labels_cache()


@pytest.fixture(autouse=True)
def export_storage(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv('EXPORT_STORAGE_DIR', str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def queued_exports(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    queued = []

    def apply_async(*args, **kwargs) -> None:
        queued.append({'args': args, 'kwargs': kwargs})

    monkeypatch.setattr(
        exports_router.generate_export,
        'apply_async',
        apply_async,
    )
    return queued


def create_export(
    client: TestClient,
    headers: dict[str, str],
    document_id: int,
    export_format: str = 'json',
) -> dict:
    response = client.post(
        '/api/v1/exports/',
        headers=headers,
        json={'document_id': document_id, 'format': export_format},
    )
    assert response.status_code == 202
    return response.json()


def run_export(export_id: int) -> None:
    async def process() -> None:
        await close_db()
        await process_export_job(export_id)
        await close_db()

    asyncio.run(process())


def create_annotation(
    client: TestClient,
    headers: dict[str, str],
    document_id: int,
    label_id: int,
    start: int,
    end: int,
) -> dict:
    response = client.post(
        '/api/v1/annotations/',
        headers=headers,
        json={
            'document': document_id,
            'label': label_id,
            'start': start,
            'end': end,
        },
    )
    assert response.status_code == 201
    return response.json()


def insert_export_job(
    user_id: int,
    document_id: int,
    export_format: str,
    file_path: str = '',
) -> int:
    async def insert() -> int:
        await close_db()
        async with async_session() as db:
            job = ExportJob(
                user_id=user_id,
                document_id=document_id,
                format=export_format,
                status=EXPORT_PENDING,
                file_path=file_path,
                created_at=utc_now(),
                error='',
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            job_id = job.id
        await close_db()
        return job_id

    return asyncio.run(insert())


def test_export_upload_returns_202_and_enqueues_task(
    client: TestClient,
    queued_exports: list[dict],
) -> None:
    headers = auth_headers(register_and_login(client, 'export-queue-user'))
    document = create_document(client, headers)

    job = create_export(client, headers, document['id'])

    assert job['status'] == 'pending'
    assert job['format'] == 'json'
    assert job['document_id'] == document['id']
    assert queued_exports == [
        {
            'args': (),
            'kwargs': {
                'args': (job['id'],),
                'queue': 'exports',
                'routing_key': 'exports',
            },
        }
    ]


def test_json_export_content_and_download(
    client: TestClient,
    queued_exports: list[dict],
) -> None:
    headers = auth_headers(register_and_login(client, 'export-json-user'))
    content = 'Начало\nкраснокожих бесов\nконец'
    document = create_document(
        client,
        headers,
        title='Явление 2',
        content=content,
    )
    label = create_label(client, headers, name='зло')
    start = content.index('краснокожих')
    end = start + len('краснокожих бесов')
    annotation = create_annotation(
        client,
        headers,
        document['id'],
        label['id'],
        start,
        end,
    )
    job = create_export(client, headers, document['id'])

    run_export(job['id'])

    status_response = client.get(
        f"/api/v1/exports/{job['id']}/",
        headers=headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()['status'] == 'completed'

    download_response = client.get(
        f"/api/v1/exports/{job['id']}/download/",
        headers=headers,
    )
    assert download_response.status_code == 200
    assert download_response.headers['content-type'] == 'application/json'
    assert 'yavlenie-2_export.json' in (
        download_response.headers['content-disposition']
    )

    payload = download_response.json()
    assert payload['schema_version'] == 2
    assert payload['document']['id'] == document['id']
    assert payload['document']['content'] == content
    assert payload['labels'] == [
        {
            'id': label['id'],
            'name': 'зло',
            'color': '#ff0000',
        }
    ]
    assert payload['annotations'] == [
        {
            'id': annotation['id'],
            'start': start,
            'end': end,
            'text': content[start:end],
            'label': {
                'id': label['id'],
                'name': 'зло',
                'color': '#ff0000',
            },
            'label_id': label['id'],
            'created_at': annotation['created_at'],
        }
    ]


def test_pending_export_cannot_be_downloaded(
    client: TestClient,
    queued_exports: list[dict],
) -> None:
    headers = auth_headers(register_and_login(client, 'export-pending-user'))
    document = create_document(client, headers)
    job = create_export(client, headers, document['id'])

    response = client.get(
        f"/api/v1/exports/{job['id']}/download/",
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()['detail'] == 'Export is not ready.'


def test_failed_export_status_and_download(
    client: TestClient,
    queued_exports: list[dict],
) -> None:
    headers = auth_headers(register_and_login(client, 'export-failed-user'))
    document = create_document(client, headers)
    job_id = insert_export_job(document['user'], document['id'], 'xml')

    run_export(job_id)

    status_response = client.get(
        f'/api/v1/exports/{job_id}/',
        headers=headers,
    )
    assert status_response.json()['status'] == 'failed'
    assert status_response.json()['error'] == 'Unsupported export format.'

    download_response = client.get(
        f'/api/v1/exports/{job_id}/download/',
        headers=headers,
    )
    assert download_response.status_code == 409


def test_user_cannot_export_foreign_document(
    client: TestClient,
    queued_exports: list[dict],
) -> None:
    owner = auth_headers(register_and_login(client, 'export-doc-owner'))
    other = auth_headers(register_and_login(client, 'export-doc-other'))
    document = create_document(client, owner)

    response = client.post(
        '/api/v1/exports/',
        headers=other,
        json={'document_id': document['id'], 'format': 'json'},
    )
    assert response.status_code == 404
    assert queued_exports == []


def test_export_status_and_download_are_visible_only_to_owner(
    client: TestClient,
    queued_exports: list[dict],
) -> None:
    owner = auth_headers(register_and_login(client, 'export-owner'))
    other = auth_headers(register_and_login(client, 'export-other'))
    document = create_document(client, owner)
    job = create_export(client, owner, document['id'])

    assert client.get(
        f"/api/v1/exports/{job['id']}/",
        headers=other,
    ).status_code == 404
    assert client.get(
        f"/api/v1/exports/{job['id']}/download/",
        headers=other,
    ).status_code == 404


def test_same_document_can_be_exported_repeatedly(
    client: TestClient,
    queued_exports: list[dict],
) -> None:
    headers = auth_headers(register_and_login(client, 'export-repeat-user'))
    document = create_document(client, headers)

    first = create_export(client, headers, document['id'])
    second = create_export(client, headers, document['id'])

    assert first['id'] != second['id']
    run_export(first['id'])
    run_export(second['id'])

    first_status = client.get(
        f"/api/v1/exports/{first['id']}/",
        headers=headers,
    )
    second_status = client.get(
        f"/api/v1/exports/{second['id']}/",
        headers=headers,
    )
    assert first_status.json()['status'] == 'completed'
    assert second_status.json()['status'] == 'completed'


def test_export_file_is_removed_when_generation_fails(
    client: TestClient,
    queued_exports: list[dict],
    export_storage,
) -> None:
    headers = auth_headers(register_and_login(client, 'export-cleanup-user'))
    document = create_document(client, headers)
    failed_path = Path(export_storage) / 'failed.json'
    failed_path.write_text('{}', encoding='utf-8')
    job_id = insert_export_job(
        document['user'],
        document['id'],
        'xml',
        str(failed_path),
    )

    run_export(job_id)

    assert not failed_path.exists()

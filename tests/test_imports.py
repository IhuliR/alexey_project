import asyncio
from io import BytesIO
from zipfile import ZipFile

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.api.routers import imports as imports_router
from app.core.config import get_settings
from app.db.session import close_db
from app.main import app
from app.services.imports import process_import_batch
from tests.test_api import (
    TEST_DATABASE_URL,
    auth_headers,
    clean_database,
    clean_labels_cache,
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
def import_storage(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv('IMPORT_STORAGE_DIR', str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def queued_imports(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    queued = []

    def apply_async(*args, **kwargs) -> None:
        queued.append({'args': args, 'kwargs': kwargs})

    monkeypatch.setattr(
        imports_router.process_import,
        'apply_async',
        apply_async,
    )
    return queued


def build_zip(files: dict[str, bytes | str]) -> bytes:
    archive = BytesIO()
    with ZipFile(archive, 'w') as zip_file:
        for filename, content in files.items():
            if isinstance(content, str):
                content = content.encode()
            zip_file.writestr(filename, content)
    return archive.getvalue()


def build_docx(text: str) -> bytes:
    data = BytesIO()
    document = Document()
    for paragraph in text.split('\n\n'):
        document.add_paragraph(paragraph)
    document.save(data)
    return data.getvalue()


def create_import(
    client: TestClient,
    headers: dict[str, str],
    archive: bytes,
) -> dict:
    response = client.post(
        '/api/v1/imports/',
        headers=headers,
        files={'file': ('batch.zip', archive, 'application/zip')},
    )
    assert response.status_code == 202
    return response.json()


def run_import(import_id: int) -> None:
    async def process() -> None:
        await close_db()
        await process_import_batch(import_id)
        await close_db()

    asyncio.run(process())


def test_import_upload_returns_202_and_enqueues_task(
    client: TestClient,
    queued_imports: list[dict],
) -> None:
    headers = auth_headers(register_and_login(client, 'import-queue-user'))
    batch = create_import(
        client,
        headers,
        build_zip({'one.txt': 'Один', 'two.txt': 'Два'}),
    )

    assert batch['status'] == 'pending'
    assert queued_imports == [
        {
            'args': (),
            'kwargs': {
                'args': (batch['id'],),
                'queue': 'imports',
                'routing_key': 'imports',
            },
        }
    ]

    run_import(batch['id'])
    status_response = client.get(
        f"/api/v1/imports/{batch['id']}/",
        headers=headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()['status'] == 'completed'


def test_import_processes_txt_docx_and_mixed_archive(
    client: TestClient,
    queued_imports: list[dict],
) -> None:
    headers = auth_headers(register_and_login(client, 'import-mixed-user'))
    batch = create_import(
        client,
        headers,
        build_zip(
            {
                'first.txt': 'Первый\r\n\r\nтекст',
                'nested/second.docx': build_docx('Второй\n\nтекст'),
            }
        ),
    )

    run_import(batch['id'])

    status_response = client.get(
        f"/api/v1/imports/{batch['id']}/",
        headers=headers,
    )
    assert status_response.json()['status'] == 'completed'
    assert status_response.json()['files_total'] == 2
    assert status_response.json()['files_processed'] == 2
    assert status_response.json()['files_failed'] == 0

    documents_response = client.get('/api/v1/documents/', headers=headers)
    documents = documents_response.json()
    assert {document['title'] for document in documents} == {
        'first',
        'second',
    }
    assert any(
        document['content'] == 'Первый\n\nтекст'
        for document in documents
    )
    assert any(
        document['content'] == 'Второй\n\nтекст'
        for document in documents
    )


def test_import_records_item_errors_and_keeps_successful_documents(
    client: TestClient,
    queued_imports: list[dict],
) -> None:
    headers = auth_headers(register_and_login(client, 'import-errors-user'))
    batch = create_import(
        client,
        headers,
        build_zip(
            {
                'valid.txt': 'Рабочий текст',
                'broken.txt': b'\xff',
                'broken.docx': b'not a docx',
                'ignored.pdf': b'%PDF',
            }
        ),
    )

    run_import(batch['id'])

    status_response = client.get(
        f"/api/v1/imports/{batch['id']}/",
        headers=headers,
    )
    assert status_response.json()['status'] == 'completed_with_errors'
    assert status_response.json()['files_total'] == 4
    assert status_response.json()['files_processed'] == 1
    assert status_response.json()['files_failed'] == 3

    items_response = client.get(
        f"/api/v1/imports/{batch['id']}/items/",
        headers=headers,
    )
    items = items_response.json()
    assert [item['status'] for item in items].count('processed') == 1
    assert [item['status'] for item in items].count('failed') == 3
    assert any(item['error'] == 'Invalid UTF-8 text file.' for item in items)
    assert any(item['error'] == 'Invalid DOCX file.' for item in items)
    assert any(
        item['error'] == 'Unsupported file extension.'
        for item in items
    )


def test_invalid_zip_marks_import_failed(
    client: TestClient,
    queued_imports: list[dict],
) -> None:
    headers = auth_headers(register_and_login(client, 'import-bad-zip-user'))
    batch = create_import(client, headers, b'not a zip')

    run_import(batch['id'])

    response = client.get(f"/api/v1/imports/{batch['id']}/", headers=headers)
    assert response.json()['status'] == 'failed'
    assert response.json()['error'] == 'Invalid ZIP archive.'


def test_unsafe_zip_path_marks_import_failed(
    client: TestClient,
    queued_imports: list[dict],
) -> None:
    headers = auth_headers(register_and_login(client, 'import-path-user'))
    batch = create_import(client, headers, build_zip({'../evil.txt': 'bad'}))

    run_import(batch['id'])

    response = client.get(f"/api/v1/imports/{batch['id']}/", headers=headers)
    assert response.json()['status'] == 'failed'
    assert response.json()['error'] == 'Archive contains unsafe paths.'


def test_archive_and_document_limits_are_checked(
    client: TestClient,
    queued_imports: list[dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = auth_headers(register_and_login(client, 'import-limits-user'))

    monkeypatch.setenv('MAX_ARCHIVE_SIZE', '5')
    get_settings.cache_clear()
    too_large_archive = client.post(
        '/api/v1/imports/',
        headers=headers,
        files={
            'file': (
                'batch.zip',
                build_zip({'small.txt': 'text'}),
                'application/zip',
            )
        },
    )
    assert too_large_archive.status_code == 400
    assert too_large_archive.json()['detail'] == 'Archive is too large.'

    monkeypatch.setenv('MAX_ARCHIVE_SIZE', str(1024 * 1024))
    monkeypatch.setenv('MAX_ARCHIVE_FILES', '1')
    get_settings.cache_clear()
    too_many_files = create_import(
        client,
        headers,
        build_zip({'one.txt': 'Один', 'two.txt': 'Два'}),
    )
    run_import(too_many_files['id'])
    files_response = client.get(
        f"/api/v1/imports/{too_many_files['id']}/",
        headers=headers,
    )
    assert files_response.json()['status'] == 'failed'
    assert files_response.json()['error'] == 'Archive contains too many files.'

    monkeypatch.setenv('MAX_ARCHIVE_FILES', '100')
    monkeypatch.setenv('MAX_DOCUMENT_SIZE', '3')
    get_settings.cache_clear()
    too_large_document = create_import(
        client,
        headers,
        build_zip({'large.txt': 'слишком большой'}),
    )
    run_import(too_large_document['id'])
    document_response = client.get(
        f"/api/v1/imports/{too_large_document['id']}/",
        headers=headers,
    )
    assert document_response.json()['status'] == 'completed_with_errors'
    assert document_response.json()['files_failed'] == 1


def test_import_status_is_visible_only_to_owner(
    client: TestClient,
    queued_imports: list[dict],
) -> None:
    owner = auth_headers(register_and_login(client, 'import-owner'))
    other = auth_headers(register_and_login(client, 'import-other'))
    batch = create_import(
        client,
        owner,
        build_zip({'owner.txt': 'Текст'}),
    )

    assert client.get(
        f"/api/v1/imports/{batch['id']}/",
        headers=other,
    ).status_code == 404
    assert client.get(
        f"/api/v1/imports/{batch['id']}/items/",
        headers=other,
    ).status_code == 404

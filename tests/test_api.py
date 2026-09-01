import asyncio
import os

import pytest
import redis
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.main import app
from app.services.labels import labels_cache_key


TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL')
TEST_REDIS_URL = os.getenv('TEST_REDIS_URL')
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason='TEST_DATABASE_URL is not configured',
)


def clean_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    if not url.database or 'test' not in url.database:
        raise RuntimeError('Tests require a database with "test" in its name')

    async def delete_test_data() -> None:
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.begin() as connection:
            await connection.execute(text('DELETE FROM core_importitem'))
            await connection.execute(text('DELETE FROM core_importbatch'))
            await connection.execute(text('DELETE FROM core_annotation'))
            await connection.execute(text('DELETE FROM core_textdocument'))
            await connection.execute(text('DELETE FROM core_label'))
            await connection.execute(text('DELETE FROM users_myuser'))
        await engine.dispose()

    asyncio.run(delete_test_data())


def clean_labels_cache() -> None:
    if not TEST_REDIS_URL:
        return

    client = redis.Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    for key in client.scan_iter(match='user:*:labels'):
        client.delete(key)
    client.close()


def run_database_statement(statement: str, **params: object) -> None:
    async def execute_statement() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        async with engine.begin() as connection:
            await connection.execute(text(statement), params)
        await engine.dispose()

    asyncio.run(execute_statement())


@pytest.fixture(autouse=True)
def empty_database() -> None:
    clean_labels_cache()
    clean_database()
    yield
    clean_database()
    clean_labels_cache()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def register_and_login(
    client: TestClient,
    username: str,
    password: str = 'Strong-test-password-42!',
) -> dict[str, str]:
    registration = client.post(
        '/api/v1/users/',
        json={'username': username, 'password': password},
    )
    assert registration.status_code == 201
    response = client.post(
        '/api/v1/jwt/create/',
        json={'username': username, 'password': password},
    )
    assert response.status_code == 200
    return response.json()


def auth_headers(tokens: dict[str, str]) -> dict[str, str]:
    return {'Authorization': f"Bearer {tokens['access']}"}


def create_document(
    client: TestClient,
    headers: dict[str, str],
    title: str = 'Документ',
    content: str = 'Начало\nнужный фрагмент\nконец',
) -> dict:
    response = client.post(
        '/api/v1/documents/',
        headers=headers,
        files={
            'title': (None, title),
            'content': (None, content),
        },
    )
    assert response.status_code == 201
    return response.json()


def create_label(
    client: TestClient,
    headers: dict[str, str],
    name: str = 'Метка',
) -> dict:
    response = client.post(
        '/api/v1/labels/',
        headers=headers,
        json={'name': name, 'color': '#ff0000'},
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def redis_client() -> redis.Redis:
    if not TEST_REDIS_URL:
        pytest.skip('TEST_REDIS_URL is not configured')

    client = redis.Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    yield client
    client.close()


def test_authentication_and_account(client: TestClient) -> None:
    tokens = register_and_login(client, 'account-user')
    headers = auth_headers(tokens)

    me_response = client.get('/api/v1/users/me/', headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()['username'] == 'account-user'
    assert set(me_response.json()) == {'id', 'username'}

    assert client.post(
        '/api/v1/jwt/verify/',
        json={'token': tokens['access']},
    ).status_code == 200
    refresh_response = client.post(
        '/api/v1/jwt/refresh/',
        json={'refresh': tokens['refresh']},
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()['access']

    password_response = client.post(
        '/api/v1/users/set_password/',
        headers=headers,
        json={
            'current_password': 'Strong-test-password-42!',
            'new_password': 'Updated-test-password-84!',
            're_new_password': 'Updated-test-password-84!',
        },
    )
    assert password_response.status_code == 204
    assert client.post(
        '/api/v1/jwt/create/',
        json={
            'username': 'account-user',
            'password': 'Updated-test-password-84!',
        },
    ).status_code == 200


def test_registration_and_authentication_errors(client: TestClient) -> None:
    register_and_login(client, 'unique-user')

    duplicate = client.post(
        '/api/v1/users/',
        json={
            'username': 'unique-user',
            'password': 'Strong-test-password-42!',
        },
    )
    assert duplicate.status_code == 400
    assert 'username' in duplicate.json()

    weak_password = client.post(
        '/api/v1/users/',
        json={'username': 'weak-user', 'password': 'password'},
    )
    assert weak_password.status_code == 400
    assert 'password' in weak_password.json()

    invalid_login = client.post(
        '/api/v1/jwt/create/',
        json={'username': 'unique-user', 'password': 'wrong-password'},
    )
    assert invalid_login.status_code == 401
    assert client.get('/api/v1/documents/').status_code == 401


def test_documents_preserve_contract_and_ownership(client: TestClient) -> None:
    owner = auth_headers(register_and_login(client, 'document-owner'))
    other = auth_headers(register_and_login(client, 'other-owner'))

    document = create_document(
        client,
        owner,
        title='Тёзка',
        content='Первый\r\n\rВторой',
    )
    duplicate = create_document(client, owner, title='Тёзка')
    foreign = create_document(client, other, title='Тёзка')

    assert document['slug'] == 'tezka'
    assert document['content'] == 'Первый\n\nВторой'
    assert duplicate['slug'] == 'tezka-2'
    assert foreign['slug'] == 'tezka'

    owner_list = client.get('/api/v1/documents/', headers=owner)
    assert {item['id'] for item in owner_list.json()} == {
        document['id'],
        duplicate['id'],
    }
    assert client.get(
        f"/api/v1/documents/{foreign['id']}/",
        headers=owner,
    ).status_code == 404

    page = client.get(
        '/api/v1/documents/?limit=1&offset=0',
        headers=owner,
    ).json()
    assert page['count'] == 2
    assert len(page['results']) == 1
    assert page['next']

    update = client.patch(
        f"/api/v1/documents/{document['id']}/",
        headers=owner,
        files={'title': (None, 'Добро и зло')},
    )
    assert update.status_code == 200
    assert update.json()['slug'] == 'dobro-i-zlo'


def test_document_upload_and_chunks(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client, 'upload-user'))
    upload = client.post(
        '/api/v1/documents/upload/',
        headers=headers,
        files={
            'file': (
                'example.txt',
                'Первый\r\n\r\nВторой'.encode(),
            )
        },
    )
    assert upload.status_code == 201
    document = upload.json()
    assert document['title'] == 'example'
    assert document['original_filename'] == 'example.txt'
    assert document['content'] == 'Первый\n\nВторой'

    chunks = client.get(
        f"/api/v1/documents/{document['id']}/chunks/?page=2&page_size=1",
        headers=headers,
    )
    assert chunks.status_code == 200
    chunk = chunks.json()
    assert chunk['chunk'] == ['Второй']
    assert (
        document['content'][chunk['chunk_start']:chunk['chunk_end']]
        == 'Второй'
    )

    invalid_extension = client.post(
        '/api/v1/documents/upload/',
        headers=headers,
        files={'file': ('example.md', b'text')},
    )
    assert invalid_extension.status_code == 400
    invalid_encoding = client.post(
        '/api/v1/documents/upload/',
        headers=headers,
        files={'file': ('example.txt', b'\xff\xfe')},
    )
    assert invalid_encoding.status_code == 400


def test_labels_are_isolated_and_unique(client: TestClient) -> None:
    owner = auth_headers(register_and_login(client, 'label-owner'))
    other = auth_headers(register_and_login(client, 'other-label-owner'))
    own_label = create_label(client, owner, 'важное')
    foreign_label = create_label(client, other, 'важное')

    response = client.get('/api/v1/labels/', headers=owner)
    assert response.json() == [own_label]

    duplicate = client.post(
        '/api/v1/labels/',
        headers=owner,
        json={'name': 'важное', 'color': '#123456'},
    )
    assert duplicate.status_code == 400
    assert 'name' in duplicate.json()
    assert client.delete(
        f"/api/v1/labels/{foreign_label['id']}/",
        headers=owner,
    ).status_code == 404


def test_labels_cache_hit_miss_invalidation_and_isolation(
    client: TestClient,
    redis_client: redis.Redis,
) -> None:
    owner = auth_headers(register_and_login(client, 'cached-label-owner'))
    other = auth_headers(register_and_login(client, 'cached-other-owner'))
    owner_id = client.get('/api/v1/users/me/', headers=owner).json()['id']
    other_id = client.get('/api/v1/users/me/', headers=other).json()['id']

    label = create_label(client, owner, 'первичная')
    owner_key = labels_cache_key(owner_id)
    assert redis_client.get(owner_key) is None

    first_response = client.get('/api/v1/labels/', headers=owner)
    assert first_response.status_code == 200
    assert first_response.json() == [label]
    assert redis_client.get(owner_key) is not None
    assert redis_client.ttl(owner_key) > 0

    run_database_statement(
        'UPDATE core_label SET name = :name WHERE id = :label_id',
        name='изменена без invalidation',
        label_id=label['id'],
    )
    cached_response = client.get('/api/v1/labels/', headers=owner)
    assert cached_response.status_code == 200
    assert cached_response.json() == [label]

    other_label = create_label(client, other, 'чужая')
    other_response = client.get('/api/v1/labels/', headers=other)
    assert other_response.status_code == 200
    assert other_response.json() == [other_label]
    assert owner_key != labels_cache_key(other_id)

    patch_response = client.patch(
        f"/api/v1/labels/{label['id']}/",
        headers=owner,
        json={'name': 'обновленная'},
    )
    assert patch_response.status_code == 200
    assert redis_client.get(owner_key) is None
    assert client.get('/api/v1/labels/', headers=owner).json() == [
        patch_response.json()
    ]

    created = create_label(client, owner, 'новая')
    assert redis_client.get(owner_key) is None
    labels_after_create = client.get('/api/v1/labels/', headers=owner).json()
    assert [item['id'] for item in labels_after_create] == [
        label['id'],
        created['id'],
    ]

    delete_response = client.delete(
        f"/api/v1/labels/{created['id']}/",
        headers=owner,
    )
    assert delete_response.status_code == 204
    assert redis_client.get(owner_key) is None
    assert client.get('/api/v1/labels/', headers=owner).json() == [
        patch_response.json()
    ]


def test_labels_list_works_when_redis_is_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import cache

    class BrokenRedis:
        async def get(self, key: str) -> None:
            raise OSError('redis is unavailable')

        async def delete(self, key: str) -> None:
            raise OSError('redis is unavailable')

        async def set(
            self,
            key: str,
            value: str,
            ex: int,
        ) -> None:
            raise OSError('redis is unavailable')

    monkeypatch.setattr(cache, 'get_redis_client', lambda: BrokenRedis())

    headers = auth_headers(register_and_login(client, 'broken-redis-owner'))
    label = create_label(client, headers, 'без redis')
    response = client.get('/api/v1/labels/', headers=headers)

    assert response.status_code == 200
    assert response.json() == [label]


def test_annotations_validate_offsets_and_ownership(
    client: TestClient,
) -> None:
    owner = auth_headers(register_and_login(client, 'annotation-owner'))
    other = auth_headers(register_and_login(client, 'other-annotation-owner'))
    document = create_document(client, owner)
    foreign_document = create_document(client, other, title='Чужой')
    label = create_label(client, owner)
    foreign_label = create_label(client, other, name='Чужая метка')
    start = document['content'].index('нужный')
    end = start + len('нужный фрагмент')

    response = client.post(
        '/api/v1/annotations/',
        headers=owner,
        json={
            'document': document['id'],
            'label': label['id'],
            'start': start,
            'end': end,
            'text': 'Недоверенный текст клиента',
        },
    )
    assert response.status_code == 201
    annotation = response.json()
    assert annotation['text'] == document['content'][start:end]

    cases = (
        ({'start': 3, 'end': 3}, 'end'),
        ({'start': -1, 'end': 3}, 'start'),
        ({'start': 0, 'end': len(document['content']) + 1}, 'end'),
        (
            {
                'start': document['content'].index('\n'),
                'end': document['content'].index('\n') + 1,
            },
            'start',
        ),
        ({'document': foreign_document['id']}, 'document'),
        ({'label': foreign_label['id']}, 'label'),
    )
    base_payload = {
        'document': document['id'],
        'label': label['id'],
        'start': 0,
        'end': 6,
    }
    for changes, error_field in cases:
        invalid = client.post(
            '/api/v1/annotations/',
            headers=owner,
            json=base_payload | changes,
        )
        assert invalid.status_code == 400
        assert error_field in invalid.json()

    own_annotations = client.get(
        f"/api/v1/annotations/?document={document['id']}",
        headers=owner,
    )
    annotation_ids = [item['id'] for item in own_annotations.json()]
    assert annotation_ids == [annotation['id']]


def test_annotation_update_and_delete_rules(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client, 'delete-owner'))
    document = create_document(client, headers, content='Добро и зло')
    label = create_label(client, headers, 'зло')
    annotation = client.post(
        '/api/v1/annotations/',
        headers=headers,
        json={
            'document': document['id'],
            'label': label['id'],
            'start': 0,
            'end': 5,
        },
    ).json()

    updated = client.patch(
        f"/api/v1/annotations/{annotation['id']}/",
        headers=headers,
        json={'start': 8, 'end': 11},
    )
    assert updated.status_code == 200
    assert updated.json()['text'] == 'зло'

    protected = client.delete(
        f"/api/v1/labels/{label['id']}/",
        headers=headers,
    )
    assert protected.status_code == 409
    assert protected.json()['code'] == 'label_in_use'
    assert protected.json()['annotations_count'] == 1

    assert client.delete(
        f"/api/v1/annotations/{annotation['id']}/",
        headers=headers,
    ).status_code == 204
    assert client.delete(
        f"/api/v1/labels/{label['id']}/",
        headers=headers,
    ).status_code == 204


def test_document_delete_cascades_annotations(client: TestClient) -> None:
    headers = auth_headers(register_and_login(client, 'cascade-owner'))
    document = create_document(client, headers)
    label = create_label(client, headers)
    client.post(
        '/api/v1/annotations/',
        headers=headers,
        json={
            'document': document['id'],
            'label': label['id'],
            'start': 0,
            'end': 6,
        },
    )

    assert client.delete(
        f"/api/v1/documents/{document['id']}/",
        headers=headers,
    ).status_code == 204
    assert client.get('/api/v1/annotations/', headers=headers).json() == []

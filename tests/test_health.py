from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_fastapi_docs() -> None:
    assert client.get('/docs').status_code == 200
    assert client.get('/redoc').status_code == 200

    response = client.get('/openapi.json')

    assert response.status_code == 200
    assert response.json()['info']['title'] == 'Formaslov API'

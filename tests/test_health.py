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
    schema = response.json()
    assert schema['info']['title'] == 'Formaslov API'

    import_operation = schema['paths']['/api/v1/imports/']['post']
    assert 'multipart/form-data' in import_operation['requestBody']['content']
    assert '400' in import_operation['responses']
    assert '422' not in import_operation['responses']

    export_operation = schema['paths']['/api/v1/exports/']['post']
    assert export_operation['responses']['202']['content'][
        'application/json'
    ]['schema']['$ref'].endswith('/ExportJobRead')
    assert '400' in export_operation['responses']
    assert '422' not in export_operation['responses']

from fastapi.testclient import TestClient

from app.main import create_app


def test_health():
    with TestClient(create_app()) as client:
        assert client.get('/api/health').json()['status'] == 'ok'

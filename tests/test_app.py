import pytest
from fastapi.testclient import TestClient

from app import create_app
from backend.config import Settings


@pytest.fixture
def client():
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as client:
        yield client


def test_health_does_not_expose_configuration(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_room_creation_is_not_simulated(client):
    assert client.post("/api/rooms", json={"question": "Example"}).status_code == 404

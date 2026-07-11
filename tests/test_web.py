import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from codeguard.web import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestWebAPI:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_create_session(self, client):
        response = client.post("/sessions", json={
            "task": "write a hello world program",
            "project_root": "/tmp/test"
        })
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_list_sessions_empty(self, client):
        response = client.get("/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data

    def test_get_session_not_found(self, client):
        response = client.get("/sessions/nonexistent")
        assert response.status_code == 404

    def test_approve_action_not_found(self, client):
        response = client.post("/sessions/nonexistent/approve")
        assert response.status_code == 404
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify that GET / returns the expected welcome response, docs, and module discovery links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Welcome to NitiSetu API" in data["message"]
    assert data["docs"] == "/docs"
    assert "modules" in data
    assert "laws" in data["modules"]
    assert "schemes" in data["modules"]
    assert "documents" in data["modules"]
    assert "chat" in data["modules"]


def test_health_check_endpoint():
    """Verify that GET /api/v1/health returns healthy status, app name, and version."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "NitiSetu API" in data["application"]
    assert data["version"] == "2.0.0"


def test_chat_test_valid_message():
    """Verify that POST /api/v1/chat/test accepts a valid query and returns dev response."""
    payload = {"message": "Explain PM Kisan scheme"}
    response = client.post("/api/v1/chat/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "development response" in data["message"]
    assert data["received_message"] == "Explain PM Kisan scheme"


def test_chat_test_empty_message_rejected():
    """Verify that POST /api/v1/chat/test rejects empty strings and whitespace-only payloads."""
    response_empty = client.post("/api/v1/chat/test", json={"message": ""})
    assert response_empty.status_code == 422

    response_whitespace = client.post("/api/v1/chat/test", json={"message": "   "})
    assert response_whitespace.status_code == 422

    response_missing = client.post("/api/v1/chat/test", json={})
    assert response_missing.status_code == 422

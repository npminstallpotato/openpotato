"""Tests for the LLM microservice (subprocess-based)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from fastapi.testclient import TestClient
from app import app, chat_with_claude

# Read config for the service key
_config_path = Path("config.json")
if _config_path.exists():
    with open(_config_path) as f:
        _cfg = json.load(f)
else:
    _cfg = {}
SERVICE_KEY = _cfg.get("POTATO_KEY", "")


def _auth(headers=None):
    """Helper: add the x-api-key header for authorized requests."""
    h = headers or {}
    if SERVICE_KEY:
        h.setdefault("x-api-key", SERVICE_KEY)
    return h


MOCK_RESPONSE = {
    "text": "Hello! How can I help you today?",
    "session_id": "mock-uuid",
}


def _mock_chat_with_claude(message, session_name):
    """Return a canned response without running the real claude subprocess."""
    return MOCK_RESPONSE


def test_health():
    """Health endpoint should work without auth."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@patch("app.chat_with_claude", _mock_chat_with_claude)
def test_chat_new_session():
    """New session_name should return a response."""
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "Hello", "session_name": "test-session"},
            headers=_auth(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == MOCK_RESPONSE["text"]


@patch("app.chat_with_claude", _mock_chat_with_claude)
def test_chat_existing_session():
    """Known session_name should return a response."""
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "Follow up", "session_name": "test-session"},
            headers=_auth(),
        )
        assert response.status_code == 200


def test_chat_missing_session_name():
    """Missing session_name should return 422."""
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "Hello"},
            headers=_auth(),
        )
        assert response.status_code == 422


def test_chat_auth_required():
    """Missing x-api-key should return 403 when service key is set."""
    if not SERVICE_KEY:
        pytest.skip("POTATO_KEY is empty — auth is disabled")

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "Hello", "session_name": "test"},
            headers={},
        )
        assert response.status_code == 403


def test_chat_wrong_api_key():
    """Wrong x-api-key should return 403 when service key is set."""
    if not SERVICE_KEY:
        pytest.skip("POTATO_KEY is empty — auth is disabled")

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"message": "Hello", "session_name": "test"},
            headers={"x-api-key": "wrong-key"},
        )
        assert response.status_code == 403

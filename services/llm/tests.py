"""Tests for the LLM microservice."""

import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import app

# Read the internal secret from config.json so tests can simulate Gateway requests
_config_path = Path("config.json")
if _config_path.exists():
    with open(_config_path) as f:
        _cfg = json.load(f)
else:
    _cfg = {}
INTERNAL_SECRET = _cfg.get("INTERNAL_SECRET", "")


def _gw(headers=None):
    """Helper: add the internal secret header that the Gateway would send."""
    h = headers or {}
    h.setdefault("x-internal-secret", INTERNAL_SECRET)
    return h


MOCK_RESPONSE = {
    "id": "test-msg",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Test response"}],
    "stop_reason": "end_turn",
}


async def _mock_query_llm(*args, **kwargs):
    """Return a canned Anthropic response without hitting the real API."""
    return MOCK_RESPONSE


def test_health():
    with TestClient(app) as client:
        response = client.get("/health", headers=_gw())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model"] == "deepseek-v4-flash"
        assert data["config_valid"] is True
        assert data["missing_keys"] == []


def _assert_anthropic_response(data):
    """Helper: verify response follows Anthropic message format."""
    assert data["type"] == "message"
    assert data["role"] == "assistant"
    assert isinstance(data["content"], list)
    text_block = next((b for b in data["content"] if b["type"] == "text"), None)
    assert text_block is not None, f"No text block in content: {data['content']}"
    assert isinstance(text_block["text"], str)
    assert len(text_block["text"]) > 0


@patch("app.query_llm", _mock_query_llm)
def test_chat_get():
    with TestClient(app) as client:
        response = client.get("/chat", params={"message": "Hello"}, headers=_gw())
        assert response.status_code == 200
        _assert_anthropic_response(response.json())


@patch("app.query_llm", _mock_query_llm)
def test_chat_post():
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "Hi there"}, headers=_gw())
        assert response.status_code == 200
        _assert_anthropic_response(response.json())


def test_chat_get_missing_message():
    with TestClient(app) as client:
        response = client.get("/chat", headers=_gw())
        assert response.status_code == 422


@patch("app.query_llm", _mock_query_llm)
def test_chat_post_empty_message():
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": ""}, headers=_gw())
        assert response.status_code == 200
        _assert_anthropic_response(response.json())

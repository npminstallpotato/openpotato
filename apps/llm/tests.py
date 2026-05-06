"""Tests for the LLM microservice."""

import os

# Ensure no API key is set so query_llm returns the placeholder
# (avoids making real HTTP calls to the LLM provider).
os.environ["LLM_API_KEY"] = ""

from fastapi.testclient import TestClient
from app import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "model": "deepseek-v4-flash"}


def _assert_anthropic_response(data, text_contains=None):
    """Helper: verify response follows Anthropic message format."""
    assert data["type"] == "message"
    assert data["role"] == "assistant"
    assert isinstance(data["content"], list)
    assert data["content"][0]["type"] == "text"
    if text_contains:
        assert text_contains in data["content"][0]["text"]


def test_chat_get():
    with TestClient(app) as client:
        response = client.get("/chat", params={"message": "Hello"})
        assert response.status_code == 200
        _assert_anthropic_response(response.json(), "Hello")


def test_chat_post():
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "Hi there"})
        assert response.status_code == 200
        _assert_anthropic_response(response.json(), "Hi there")


def test_chat_get_missing_message():
    with TestClient(app) as client:
        response = client.get("/chat")
        assert response.status_code == 422


def test_chat_post_empty_message():
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": ""})
        assert response.status_code == 200
        _assert_anthropic_response(response.json())

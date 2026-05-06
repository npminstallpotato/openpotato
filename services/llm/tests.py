"""Tests for the LLM microservice."""

from fastapi.testclient import TestClient
from app import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "model": "deepseek-v4-flash"}


def _assert_anthropic_response(data):
    """Helper: verify response follows Anthropic message format."""
    assert data["type"] == "message"
    assert data["role"] == "assistant"
    assert isinstance(data["content"], list)
    # Find the text block — DeepSeek may include thinking blocks before it
    text_block = next((b for b in data["content"] if b["type"] == "text"), None)
    assert text_block is not None, f"No text block in content: {data['content']}"
    assert isinstance(text_block["text"], str)
    assert len(text_block["text"]) > 0


def test_chat_get():
    with TestClient(app) as client:
        response = client.get("/chat", params={"message": "Hello"})
        assert response.status_code == 200
        _assert_anthropic_response(response.json())


def test_chat_post():
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "Hi there"})
        assert response.status_code == 200
        _assert_anthropic_response(response.json())


def test_chat_get_missing_message():
    with TestClient(app) as client:
        response = client.get("/chat")
        assert response.status_code == 422


def test_chat_post_empty_message():
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": ""})
        assert response.status_code == 200
        _assert_anthropic_response(response.json())

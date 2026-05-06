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


def test_chat_get():
    with TestClient(app) as client:
        response = client.get("/chat", params={"message": "Hello"})
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "Hello" in data["reply"]


def test_chat_post():
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "Hi there"})
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "Hi there" in data["reply"]


def test_chat_get_missing_message():
    with TestClient(app) as client:
        response = client.get("/chat")
        assert response.status_code == 422


def test_chat_post_empty_message():
    with TestClient(app) as client:
        response = client.post("/chat", json={"message": ""})
        assert response.status_code == 200

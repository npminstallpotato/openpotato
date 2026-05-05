"""Tests for the LLM microservice."""

import sys
sys.dont_write_bytecode = True

from fastapi.testclient import TestClient
from app import app, _Config

# Ensure no API key is set during tests so query_llm returns the placeholder
# (avoids making real HTTP calls to the LLM provider).
_Config.api_key = ""

# Use TestClient WITHOUT context manager so startup events don't run.
# This keeps _Config at its default values (api_key="" → placeholder reply).
client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model": "deepseek-v4-flash"}


def test_chat_get():
    response = client.get("/chat", params={"message": "Hello"})
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "Hello" in data["reply"]


def test_chat_post():
    response = client.post("/chat", json={"message": "Hi there"})
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "Hi there" in data["reply"]


def test_chat_get_missing_message():
    response = client.get("/chat")
    assert response.status_code == 422


def test_chat_post_empty_message():
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 200

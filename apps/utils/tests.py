"""Tests for the Config microservice."""

import sys
sys.dont_write_bytecode = True

from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_config_full():
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "llm" in data


def test_get_config_section():
    response = client.get("/config/llm")
    assert response.status_code == 200
    data = response.json()
    assert "value" in data
    assert "model" in data["value"]


def test_get_config_deep():
    response = client.get("/config/llm/model")
    assert response.status_code == 200
    assert "value" in response.json()


def test_get_config_port():
    response = client.get("/config/llm_port")
    assert response.status_code == 200
    assert isinstance(response.json()["value"], int)


def test_get_config_not_found():
    response = client.get("/config/nonexistent")
    assert response.status_code == 404


def test_get_config_deep_not_found():
    response = client.get("/config/llm/nonexistent")
    assert response.status_code == 404


@patch("app.load_config", return_value={})
def test_health_no_config(mock_load):
    response = client.get("/health")
    assert response.status_code == 503


@patch("app.load_config", return_value={})
def test_get_config_no_config(mock_load):
    response = client.get("/config")
    assert response.status_code == 404

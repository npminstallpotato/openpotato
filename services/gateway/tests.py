"""Tests for the Gateway microservice."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from app import app

# Read the actual API key from config.json so tests stay in sync
_config_path = Path("config.json")
if _config_path.exists():
    with open(_config_path) as f:
        _cfg = json.load(f)
else:
    _cfg = {}
API_KEY = _cfg.get("GATEWAY_API_KEY", "")


def _api(headers=None, **kwargs):
    """Helper: add API key header to requests that need it."""
    h = headers or {}
    if "X-API-Key" not in h:
        h["X-API-Key"] = API_KEY
    return h


def test_static_index():
    """Gateway serves the UI index.html."""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


def test_static_style():
    """Gateway serves style.css."""
    with TestClient(app) as client:
        response = client.get("/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]


def test_static_js():
    """Gateway serves app.js."""
    with TestClient(app) as client:
        response = client.get("/app.js")
        assert response.status_code == 200
        assert "text/javascript" in response.headers["content-type"]


def test_config_endpoint():
    """GET /api/config returns config with API key redacted."""
    with TestClient(app) as client:
        response = client.get("/api/config", headers=_api())
        assert response.status_code == 200
        data = response.json()
        assert "llm" in data
        assert data["llm"]["api_key"] == "***"
        assert "llm_port" in data
        assert "gateway_port" in data


def test_proxy_llm_unavailable():
    """Proxying to LLM returns 502 when LLM is not running."""
    with TestClient(app) as client:
        response = client.get("/api/llm/health", headers=_api())
        assert response.status_code == 502
        data = response.json()
        assert "error" in data


def test_auth_required():
    """API routes reject requests without the correct X-API-Key."""
    with TestClient(app) as client:
        # No key → 401
        resp = client.get("/api/config")
        assert resp.status_code == 401

        # Wrong key → 401
        resp = client.get("/api/config", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401

        # Correct key → 200
        resp = client.get("/api/config", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200

        # Static files still open without key
        resp = client.get("/")
        assert resp.status_code == 200

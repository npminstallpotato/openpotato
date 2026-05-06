"""Tests for the Gateway microservice."""

import os

# Disable auth + API key for tests so they don't depend on .env
os.environ["GATEWAY_API_KEY"] = ""
os.environ["LLM_API_KEY"] = ""

from fastapi.testclient import TestClient
from app import app


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
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "llm" in data
        assert data["llm"]["api_key"] == "***"
        assert "llm_port" in data
        assert "gateway_port" in data


def test_proxy_llm_unavailable():
    """Proxying to LLM returns 502 when LLM is not running."""
    with TestClient(app) as client:
        response = client.get("/api/llm/health")
        assert response.status_code == 502
        data = response.json()
        assert "error" in data


def test_auth_required():
    """API routes reject requests without the correct X-API-Key."""
    # Test with key set via env
    os.environ["GATEWAY_API_KEY"] = "test-key"
    # Reimport app module to pick up new env
    import importlib
    import app as gateway_app
    importlib.reload(gateway_app)
    app2 = gateway_app.app

    with TestClient(app2) as client:
        # No key → 401
        resp = client.get("/api/config")
        assert resp.status_code == 401

        # Wrong key → 401
        resp = client.get("/api/config", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401

        # Correct key → 200
        resp = client.get("/api/config", headers={"X-API-Key": "test-key"})
        assert resp.status_code == 200

        # Static files still open without key
        resp = client.get("/")
        assert resp.status_code == 200

    # Reset for other tests
    os.environ["GATEWAY_API_KEY"] = ""

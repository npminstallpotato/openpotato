"""Tests for the Gateway microservice."""

from unittest.mock import patch

from fastapi.responses import Response
from fastapi.testclient import TestClient
from app import app


async def _mock_proxy_error(*args, **kwargs):
    """Mock proxy that simulates a backend being unreachable."""
    import json
    return Response(
        content=json.dumps({"error": "Backend at http://127.0.0.1:8002 unavailable"}),
        status_code=502,
        media_type="application/json",
    )


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
    with patch("app.proxy", _mock_proxy_error), TestClient(app) as client:
        response = client.get("/api/llm/health")
        assert response.status_code == 502
        data = response.json()
        assert "error" in data

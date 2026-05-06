"""FastAPI Gateway — serves UI and proxies API requests to the LLM service."""

import json
import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config from environment ────────────────────────────────────────────────

load_dotenv()

GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8000"))
GATEWAY_HOST = os.getenv("GATEWAY_HOST", "127.0.0.1")
LLM_HOST = os.getenv("LLM_HOST", "127.0.0.1")
LLM_PORT = int(os.getenv("LLM_PORT", "8002"))
LLM_BASE = f"http://{LLM_HOST}:{LLM_PORT}"
GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "")

UI_DIR = Path(__file__).resolve().parent / "ui"

# ── Lifespan — shared HTTP client ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Create a shared HTTP client for the app's lifetime."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        application.state.client = client
        logger.info("Gateway ready — proxying to LLM at %s", LLM_BASE)
        yield


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OpenPotato Gateway",
    version="0.1.0",
    lifespan=lifespan,
)


async def proxy(path: str, request: Request, base_url: str) -> Response:
    """Forward a request to the given base_url and return the response."""
    query = urlencode(dict(request.query_params))
    url = f"{base_url}/{path}"
    if query:
        url += f"?{query}"

    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }

    body = await request.body()

    try:
        resp = await request.app.state.client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body or None,
        )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
        )
    except httpx.ConnectError:
        logger.error("Cannot connect to %s", base_url)
        return Response(
            content=json.dumps({"error": f"Backend at {base_url} unavailable"}),
            status_code=502,
            media_type="application/json",
        )


# ── Config endpoint (for UI) ───────────────────────────────────────────────

@app.get("/api/config")
async def get_config():
    """Return the current config (API key redacted)."""
    return {
        "llm": {
            "model": os.getenv("LLM_MODEL", "deepseek-v4-flash"),
            "base_url": os.getenv("LLM_BASE_URL", "https://api.deepseek.com/anthropic"),
            "api_key": "***",
        },
        "llm_port": LLM_PORT,
        "gateway_port": GATEWAY_PORT,
    }


# ── API Proxy routes ───────────────────────────────────────────────────────

@app.api_route("/api/llm/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_llm(path: str, request: Request):
    return await proxy(path, request, LLM_BASE)


# ── Static UI files (must be last — catch-all) ─────────────────────────────

app.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=GATEWAY_HOST, port=GATEWAY_PORT, reload=True)

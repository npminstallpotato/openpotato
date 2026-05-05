"""FastAPI Gateway — serves UI and proxies API requests to backend services."""

import sys
sys.dont_write_bytecode = True

import json
import logging
from pathlib import Path
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent.parent / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    logger.warning("config.json not found — using defaults")
    return {}

config = load_config()

GATEWAY_PORT = config.get("gateway_port", 8000)
LLM_BASE = config.get("gateway", {}).get("llm_base", "http://localhost:8002")
UTILS_BASE = config.get("gateway", {}).get("utils_base", "http://localhost:8001")
UI_DIR = Path(__file__).resolve().parent / "ui"

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OpenPotato Gateway",
    version="0.1.0",
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
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


# ── API Proxy routes ─────────────────────────────────────────────────────────

@app.api_route("/api/llm/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_llm(path: str, request: Request):
    return await proxy(path, request, LLM_BASE)


@app.api_route("/api/utils/{path:path}", methods=["GET"])
async def proxy_utils(path: str, request: Request):
    return await proxy(path, request, UTILS_BASE)


# ── Static UI files (must be last — catch-all) ──────────────────────────────

app.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=GATEWAY_PORT, reload=True)

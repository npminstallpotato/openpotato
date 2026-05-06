"""FastAPI Gateway — serves UI and proxies API requests to the LLM service."""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from starlette.responses import FileResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config / Settings paths ─────────────────────────────────────────────────

CONFIG_PATH = Path("config.json")
SETTINGS_PATH = Path("settings.json")

# config.json — read once at startup (infrastructure / secrets)
_config = {}
if CONFIG_PATH.exists():
    with open(CONFIG_PATH) as f:
        _config = json.load(f)
    logger.info("Config loaded from %s", CONFIG_PATH)
else:
    logger.warning("config.json not found at %s — using defaults", CONFIG_PATH)

HOST = _config.get("HOST", "127.0.0.1")
GATEWAY_PORT = int(_config.get("GATEWAY_PORT", "8000"))
LLM_PORT = int(_config.get("LLM_PORT", "8002"))
LLM_BASE = f"http://{HOST}:{LLM_PORT}"
UTIL_PORT = int(_config.get("UTIL_PORT", "8001"))
UTIL_BASE = f"http://{HOST}:{UTIL_PORT}"
INTERNAL_SECRET = _config.get("INTERNAL_SECRET", "")


def load_settings() -> dict:
    """Read settings.json (live-reloaded on every call)."""
    try:
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

UI_DIR = Path("services/gateway/ui")

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

# ── Required config validation dependency ──────────────────────────────────

GATEWAY_REQUIRED_KEYS = ["LLM_PORT"]


def check_gateway_config():
    """FastAPI dependency: verify the Gateway has the config it needs to proxy.

    LLM_PORT is required for the proxy to know where the LLM
    service lives.  If config.json is missing or incomplete, returns 503.
    """
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = json.load(f)

    missing = [key for key in GATEWAY_REQUIRED_KEYS if not config.get(key)]
    if missing:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Gateway configuration incomplete",
                "missing_keys": missing,
                "hint": f"Set {', '.join(missing)} in config.json",
            },
        )
    return config


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
    headers["x-internal-secret"] = INTERNAL_SECRET

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
    except httpx.RequestError:
        logger.error("Request to %s failed", base_url)
        return Response(
            content=json.dumps({"error": f"Backend at {base_url} unreachable or timed out"}),
            status_code=502,
            media_type="application/json",
        )


# ── Config endpoint (for UI — live-reloads settings.json) ──────────────────

@app.get("/api/config")
async def get_config():
    """Return the current settings (API key redacted) + infrastructure ports."""
    settings = load_settings()
    return {
        "llm": {
            "model": settings.get("LLM_MODEL", "deepseek-v4-flash"),
            "base_url": settings.get("LLM_BASE_URL", "https://api.deepseek.com/anthropic"),
            "api_key": "***",
        },
        "llm_port": LLM_PORT,
        "gateway_port": GATEWAY_PORT,
    }


# ── API Proxy routes ───────────────────────────────────────────────────────

@app.api_route("/api/llm/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_llm(path: str, request: Request, _=Depends(check_gateway_config)):
    return await proxy(path, request, LLM_BASE)


@app.api_route("/api/settings", methods=["GET", "PUT"])
async def proxy_settings(request: Request):
    """Proxy settings CRUD to the Util microservice."""
    return await proxy("api/settings", request, UTIL_BASE)


# ── Static files + SPA routing ─────────────────────────────────────────

@app.get("/{path:path}")
async def spa_or_static(path: str):
    """Serve static files (style.css, app.js) directly, otherwise serve
    index.html for client-side routing (/chat, /settings, etc.)."""
    if not path:
        # Root "/" — serve index.html
        return FileResponse(str(UI_DIR / "index.html"))
    file_path = (UI_DIR / path).resolve()
    # Prevent directory traversal
    if not str(file_path).startswith(str(UI_DIR.resolve())):
        return Response("Forbidden", status_code=403)
    if file_path.is_file():
        return FileResponse(str(file_path))
    return FileResponse(str(UI_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=GATEWAY_PORT, reload=True)

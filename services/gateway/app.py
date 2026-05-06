"""FastAPI Gateway — serves UI and proxies API requests to the LLM service."""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config from config.json (initial load for auth/proxy settings) ─────────

CONFIG_PATH = Path("config.json")

_config = {}
if CONFIG_PATH.exists():
    with open(CONFIG_PATH) as f:
        _config = json.load(f)
    logger.info("Config loaded from %s", CONFIG_PATH)
else:
    logger.warning("config.json not found at %s — using defaults", CONFIG_PATH)

GATEWAY_PORT = int(_config.get("GATEWAY_PORT", "8000"))
GATEWAY_HOST = _config.get("GATEWAY_HOST", "127.0.0.1")
LLM_HOST = _config.get("LLM_HOST", "127.0.0.1")
LLM_PORT = int(_config.get("LLM_PORT", "8002"))
LLM_BASE = f"http://{LLM_HOST}:{LLM_PORT}"
GATEWAY_API_KEY = _config.get("GATEWAY_API_KEY", "")

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

# ── API key auth middleware ────────────────────────────────────────────────

AUTH_REQUIRED = bool(GATEWAY_API_KEY)

if not AUTH_REQUIRED:
    logger.warning("GATEWAY_API_KEY not set — API endpoints have no authentication")

# ── Required config validation dependency ──────────────────────────────────

GATEWAY_REQUIRED_KEYS = ["LLM_HOST", "LLM_PORT"]


def check_gateway_config():
    """FastAPI dependency: verify the Gateway has the config it needs to proxy.

    LLM_HOST and LLM_PORT are required for the proxy to know where the LLM
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


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Require X-API-Key on /api/* routes for external requests.
    Same-origin requests from the browser UI are trusted automatically.
    """
    if AUTH_REQUIRED and request.url.path.startswith("/api/"):
        origin = request.headers.get("origin", "")
        # Same-origin = browser fetch from the UI (trusted)
        if origin and origin == f"http://{request.url.hostname}:{request.url.port}":
            return await call_next(request)
        # External clients must provide the correct key
        if request.headers.get("x-api-key", "") != GATEWAY_API_KEY:
            return JSONResponse(
                content={"error": "Invalid or missing API key"},
                status_code=401,
            )
    return await call_next(request)


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


# ── Config endpoint (for UI — live-reloads config.json) ────────────────────

@app.get("/api/config")
async def get_config(_=Depends(check_gateway_config)):
    """Return the current config (API key redacted)."""
    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = json.load(f)

    return {
        "llm": {
            "model": config.get("LLM_MODEL", "deepseek-v4-flash"),
            "base_url": config.get("LLM_BASE_URL", "https://api.deepseek.com/anthropic"),
            "api_key": "***",
        },
        "llm_port": int(config.get("LLM_PORT", "8002")),
        "gateway_port": int(config.get("GATEWAY_PORT", "8000")),
    }


# ── API Proxy routes ───────────────────────────────────────────────────────

@app.api_route("/api/llm/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_llm(path: str, request: Request, _=Depends(check_gateway_config)):
    return await proxy(path, request, LLM_BASE)


# ── Static UI files (must be last — catch-all) ─────────────────────────────

app.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=GATEWAY_HOST, port=GATEWAY_PORT, reload=True)

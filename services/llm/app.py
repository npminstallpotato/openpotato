"""FastAPI LLM microservice — config loaded from config.json.

Uses Anthropic-compatible API format (x-api-key auth, /messages endpoint).
Returns the full Anthropic response body.
"""

import json
import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Query, Request
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config from config.json, falling back to env vars ──────────────────────

_config_path = Path(__file__).resolve().parent.parent / "config.json"
if _config_path.exists():
    with open(_config_path) as _f:
        for _k, _v in json.load(_f).items():
            if _k not in os.environ:  # don't override existing env vars
                os.environ[_k] = str(_v)
    logger.info("Loaded config from %s", _config_path)
else:
    logger.warning("config.json not found at %s — using env vars / defaults", _config_path)

API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/anthropic")
PORT = int(os.getenv("LLM_PORT", "8002"))

# ── Lifespan — shared HTTP client ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Create a shared HTTP client for the app's lifetime."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        application.state.client = client
        logger.info("LLM service ready — model=%s", MODEL)
        yield


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LLM Microservice",
    description="Proxy requests to an LLM provider.",
    version="0.1.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    message: str


async def query_llm(message: str, client: httpx.AsyncClient) -> dict:
    """Send message to LLM provider and return the full Anthropic response."""
    if not API_KEY:
        logger.warning("LLM_API_KEY not set — returning placeholder")
        return {
            "id": "placeholder",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f'[Placeholder] Received: "{message}". '
                        "Set LLM_API_KEY in .env to connect a real provider."
                    ),
                }
            ],
            "stop_reason": "end_turn",
        }

    resp = await client.post(
        f"{BASE_URL}/messages",
        headers={
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": 4096,
        },
    )

    if resp.status_code != 200:
        logger.error("LLM provider error: %s %s", resp.status_code, resp.text[:300])
        return {
            "id": "error",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": f"Error: LLM provider returned {resp.status_code}.",
                }
            ],
            "stop_reason": "error",
        }

    return resp.json()


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL}


@app.post("/chat")
async def chat(body: ChatRequest, request: Request):
    logger.info("chat request: %s", body.message[:80])
    return await query_llm(body.message, request.app.state.client)


@app.get("/chat")
async def chat_get(
    message: str = Query(..., description="Message to send"),
    request: Request = None,
):
    logger.info("chat GET request: %s", message[:80])
    return await query_llm(message, request.app.state.client)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=PORT, reload=True)

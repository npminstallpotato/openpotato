"""FastAPI LLM microservice — config loaded from config.json.

Uses Anthropic-compatible API format (x-api-key auth, /messages endpoint).
Returns the full Anthropic response body.
"""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Query, Request
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config from config.json (live-reloaded on every request) ───────────────

CONFIG_PATH = Path("config.json")

def load_config():
    """Read config.json and return as dict. Returns {} on error."""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

PORT = int(load_config().get("LLM_PORT", "8002"))

if CONFIG_PATH.exists():
    logger.info("Config loaded from %s", CONFIG_PATH)
else:
    logger.warning("config.json not found at %s — using defaults", CONFIG_PATH)

# ── Lifespan — shared HTTP client ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Create a shared HTTP client for the app's lifetime."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        application.state.client = client
        logger.info("LLM service ready — port=%s", PORT)
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
    config = load_config()
    api_key = config.get("LLM_API_KEY", "")
    model = config.get("LLM_MODEL", "deepseek-v4-flash")
    base_url = config.get("LLM_BASE_URL", "https://api.deepseek.com/anthropic")

    if not api_key:
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
                        "Set LLM_API_KEY in config.json to connect a real provider."
                    ),
                }
            ],
            "stop_reason": "end_turn",
        }

    resp = await client.post(
        f"{base_url}/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": model,
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
    config = load_config()
    model = config.get("LLM_MODEL", "deepseek-v4-flash")
    return {"status": "ok", "model": model}


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

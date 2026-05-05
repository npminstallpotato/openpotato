"""FastAPI LLM microservice — fetches config from Utils service."""

import sys
sys.dont_write_bytecode = True  # prevent __pycache__

import logging

import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Bootstrap config ──────────────────────────────────────────────────────

UTILS_BASE = "http://localhost:8001"


async def fetch_config() -> dict:
    """Get config from the Utils microservice. Returns {} if unreachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{UTILS_BASE}/config")
        if resp.status_code == 200:
            data = resp.json()
            logger.info("Config fetched from Utils service")
            return data
        logger.warning("Utils returned %s — using defaults", resp.status_code)
    except httpx.ConnectError:
        logger.warning("Cannot reach Utils at %s — using defaults", UTILS_BASE)
    return {}


# ── Mutable config store (populated at startup) ────────────────────────────

class _Config:
    """Simple mutable holder so endpoints can read live values."""
    api_key: str = ""
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com/v1"
    port: int = 8002

    @classmethod
    def update(cls, cfg: dict) -> None:
        llm = cfg.get("llm", {})
        cls.api_key = llm.get("api_key", "")
        cls.model = llm.get("model", cls.model)
        cls.base_url = llm.get("base_url", cls.base_url)
        cls.port = cfg.get("llm_port", cls.port)


# ── Lifespan (replaces deprecated on_event) ────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Fetch config from Utils on startup, clean up on shutdown."""
    cfg = await fetch_config()
    _Config.update(cfg)
    logger.info("LLM service ready — model=%s port=%d", _Config.model, _Config.port)
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


class ChatResponse(BaseModel):
    reply: str


async def query_llm(message: str) -> str:
    """Send message to LLM provider and return the reply text."""
    if not _Config.api_key:
        logger.warning("LLM_API_KEY not set — returning placeholder")
        return (
            f'[Placeholder] Received: "{message}". '
            "Set LLM_API_KEY in config.json to connect a real provider."
        )

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{_Config.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {_Config.api_key}"},
            json={
                "model": _Config.model,
                "messages": [{"role": "user", "content": message}],
            },
        )

        if resp.status_code != 200:
            logger.error("LLM provider error: %s %s", resp.status_code, resp.text[:300])
            return f"Error: LLM provider returned {resp.status_code}."

        body = resp.json()
        return body["choices"][0]["message"]["content"]


@app.get("/health")
async def health():
    return {"status": "ok", "model": _Config.model}


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    logger.info("chat request: %s", body.message[:80])
    reply = await query_llm(body.message)
    return ChatResponse(reply=reply)


@app.get("/chat", response_model=ChatResponse)
async def chat_get(message: str = Query(..., description="Message to send")):
    logger.info("chat GET request: %s", message[:80])
    reply = await query_llm(message)
    return ChatResponse(reply=reply)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=_Config.port, reload=True)

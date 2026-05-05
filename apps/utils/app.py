"""FastAPI Config microservice — single file app."""

import sys
sys.dont_write_bytecode = True

import json
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.json"


def load_config() -> dict:
    """Load config.json from project root. Returns empty dict if missing."""
    if not CONFIG_PATH.exists():
        logger.warning("config.json not found at %s", CONFIG_PATH)
        return {}
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.error("config.json is not a valid JSON object")
            return {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load config.json: %s", e)
        return {}


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Config Microservice",
    description="Centralized config provider for OpenPotato microservices.",
    version="0.1.0",
)


@app.get("/health")
async def health():
    """Health check — returns 503 if config is missing or empty."""
    config = load_config()
    if not config:
        raise HTTPException(status_code=503, detail="config.json missing or invalid")
    return {"status": "ok"}


@app.get("/config")
async def get_config():
    """Return the full config object."""
    config = load_config()
    if not config:
        raise HTTPException(status_code=404, detail="config.json not found or empty")
    return config


@app.get("/config/{path:path}")
async def get_config_path(path: str):
    """
    Return a specific config value by path.

    Examples:
      GET /config/llm           → {"value": {"api_key": "...", ...}}
      GET /config/llm/model     → {"value": "deepseek-v4-flash"}
      GET /config/llm_port      → {"value": 8002}
    """
    config = load_config()
    if not config:
        raise HTTPException(status_code=404, detail="config.json not found or empty")

    keys = path.strip("/").split("/")
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Config key '{path}' not found",
            )
    return {"value": current}


if __name__ == "__main__":
    import uvicorn

    # Read port from config if available, else default
    cfg = load_config()
    port = cfg.get("utils_port", 8001)
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)

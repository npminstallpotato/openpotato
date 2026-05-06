"""FastAPI Util microservice — manages settings.json (LLM config)."""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config from config.json (read once at startup) ─────────────────────────

CONFIG_PATH = Path("config.json")

_config = {}
if CONFIG_PATH.exists():
    with open(CONFIG_PATH) as f:
        _config = json.load(f)
    logger.info("Config loaded from %s", CONFIG_PATH)
else:
    logger.warning("config.json not found — using defaults")

PORT = int(_config.get("UTIL_PORT", "8001"))
HOST = _config.get("HOST", "127.0.0.1")
INTERNAL_SECRET = _config.get("INTERNAL_SECRET", "")

# ── Settings path ──────────────────────────────────────────────────────────

SETTINGS_PATH = Path("settings.json")
DEFAULTS_PATH = Path("settings.example.json")

SETTINGS_KEYS = ["LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL"]

DEFAULT_SETTINGS = {
    "LLM_API_KEY": "",
    "LLM_MODEL": "deepseek-v4-flash",
    "LLM_BASE_URL": "https://api.deepseek.com/anthropic",
}


def load_settings() -> dict:
    """Read settings.json, return dict (fall back to defaults)."""
    try:
        with open(SETTINGS_PATH) as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)


def save_settings(data: dict):
    """Write settings.json, preserving only known keys."""
    cleaned = {k: data[k] for k in SETTINGS_KEYS if k in data}
    with open(SETTINGS_PATH, "w") as f:
        json.dump(cleaned, f, indent=2)
        f.write("\n")
    logger.info("Settings saved to %s", SETTINGS_PATH)


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Util Microservice",
    description="Read/write settings.json",
    version="0.1.0",
)


def check_internal_origin(request: Request):
    """Only allow requests that come through the Gateway."""
    if request.headers.get("x-internal-secret", "") != INTERNAL_SECRET:
        raise HTTPException(
            status_code=403,
            detail="Direct access not allowed — use the Gateway on port 8000",
        )


class SettingsUpdate(BaseModel):
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    LLM_BASE_URL: str = ""


@app.get("/health")
async def health():
    """Return service health."""
    settings = load_settings()
    has_key = bool(settings.get("LLM_API_KEY"))
    return {
        "status": "ok",
        "has_api_key": has_key,
        "model": settings.get("LLM_MODEL", ""),
    }


@app.get("/api/settings")
async def get_settings():
    """Return current settings."""
    settings = load_settings()
    return {
        "LLM_MODEL": settings.get("LLM_MODEL", ""),
        "LLM_BASE_URL": settings.get("LLM_BASE_URL", ""),
        "LLM_API_KEY": settings.get("LLM_API_KEY", ""),
    }


@app.put("/api/settings")
async def put_settings(body: SettingsUpdate):
    """Update and persist settings.json."""
    current = load_settings()
    current.update(body.model_dump(exclude_unset=True))
    save_settings(current)
    return {"status": "ok", "message": "Settings saved"}


@app.get("/api/settings/defaults")
async def get_default_settings():
    """Return default settings from settings.example.json."""
    try:
        with open(DEFAULTS_PATH) as f:
            defaults = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        defaults = dict(DEFAULT_SETTINGS)
    return defaults


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True)

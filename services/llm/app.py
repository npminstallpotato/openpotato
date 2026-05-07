"""FastAPI LLM microservice — wraps the claude CLI as a subprocess.

Standalone server: no gateway dependency. Authenticates via x-api-key header.
Sessions are managed by resuming via `-r <name> --fork-session` (existing) or
creating with `--name <name>` (new). A local .claude/sessions.json tracks
which session names have been created.
"""

import json
import logging
import subprocess
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
    logger.warning("config.json not found at %s — using defaults", CONFIG_PATH)

PORT = int(_config.get("LLM_PORT", "8002"))
HOST = _config.get("HOST", "127.0.0.1")
POTATO_KEY = _config.get("POTATO_KEY", "")

# ── Project paths ──────────────────────────────────────────────────────────

PROJECT_ROOT = Path(".").resolve()
SESSIONS_PATH = Path(".claude/sessions.json")


def load_known_sessions() -> list:
    """Read the list of known session names from disk."""
    try:
        with open(SESSIONS_PATH) as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_known_sessions(names: list):
    """Persist the list of known session names to disk."""
    SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSIONS_PATH, "w") as f:
        json.dump(names, f, indent=2)
        f.write("\n")


def chat_with_claude(message: str, session_name: str) -> dict:
    """Run claude --print, creating or resuming a session by name.

    Uses --fork-session on resume to avoid the 'session in use' lock that
    Claude Code holds on recently-active sessions.

    Returns the parsed JSON output from the claude CLI.
    """
    known = load_known_sessions()

    if session_name in known:
        cmd = [
            "claude", "--print", "--output-format", "json",
            "-r", session_name, "--fork-session",
            message,
        ]
        logger.info("Resuming session '%s'", session_name)
    else:
        cmd = [
            "claude", "--print", "--output-format", "json",
            "--name", session_name,
            message,
        ]
        known.append(session_name)
        save_known_sessions(known)
        logger.info("Created new session '%s'", session_name)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=120,
    )

    if result.returncode != 0:
        # If resuming an old session that Claude Code no longer has, create fresh
        if session_name in known:
            logger.warning("Failed to resume '%s' — creating fresh", session_name)
            cmd = [
                "claude", "--print", "--output-format", "json",
                "--name", session_name,
                message,
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=PROJECT_ROOT, timeout=120,
            )

    if result.returncode != 0:
        stderr = result.stderr[:500] if result.stderr else ""
        logger.error("claude exited %d: %s", result.returncode, stderr)
        raise HTTPException(
            status_code=502,
            detail=f"claude exited {result.returncode}: {stderr}",
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse claude output: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse claude response: {e}",
        )


# ── Auth dependency ────────────────────────────────────────────────────────


def check_api_key(request: Request):
    """Verify the x-api-key header matches the configured service key.

    If POTATO_KEY is empty, auth is skipped (allow all).
    """
    if not POTATO_KEY:
        return
    header_key = request.headers.get("x-api-key", "")
    if header_key != POTATO_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LLM Microservice",
    description="Standalone chat server wrapping the claude CLI.",
    version="0.2.0",
)


class ChatRequest(BaseModel):
    message: str
    session_name: str


@app.get("/health")
async def health():
    """Return service health status."""
    return {"status": "ok"}


@app.post("/chat")
async def chat(body: ChatRequest, request: Request):
    """Send a message to a named session.

    If session_name is new, a session is created.
    If session_name exists, the conversation is resumed.
    """
    check_api_key(request)
    logger.info("chat: session=%s message=%.80s", body.session_name, body.message)
    return await _run_chat(body.message, body.session_name)


async def _run_chat(message: str, session_name: str) -> dict:
    """Run chat_with_claude in a thread to avoid blocking the event loop.

    subprocess.run is synchronous — offload it so the event loop stays responsive.
    """
    import asyncio
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, chat_with_claude, message, session_name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True)

# OpenPotato 🥔

> AI agents at your command, powered by your preferred LLM — built 100% by AI.
> Updated: 2026-05-06

## Project Structure

```
OpenPotato/
├── services/
│   ├── gateway/
│   │   ├── app.py       # FastAPI gateway — serves UI + proxies to LLM
│   │   ├── tests.py     # Gateway tests
│   │   └── ui/          # Static frontend (index.html, style.css, app.js)
│   └── llm/
│       ├── app.py       # LLM microservice — DeepSeek API calls via Anthropic format
│       └── tests.py
├── .claude/             # Claude project settings
├── .config/             # Local Claude CLI config (gitignored)
├── config.json          # Local config with API keys (gitignored)
├── config.example.json  # Config template (tracked, safe defaults)
├── CLAUDE.md            # Project memory for Claude
├── CONTRIBUTING.md      # Commit convention guide
├── LICENSE              # MIT license
├── README.md
├── requirements.txt
├── install.sh           # Setup script (venv + deps + config.json)
├── start.sh             # Launch services
└── stop.sh              # Stop services
```

## Git Status

- **Branch:** `main`
- **Remote:** `origin` → `https://github.com/npminstallpotato/openpotato.git`
- **Latest commit:** `refactor: use simple relative paths, remove Path(__file__) traversal`

## Architecture

Two independent FastAPI microservices — each loads config from `config.json` on every request:

| Service     | Port | Role                                    |
|-------------|------|-----------------------------------------|
| **LLM**     | 8002 | Proxies chat requests to DeepSeek API   |
| **Gateway** | 8000 | Serves the UI + proxies `/api/llm/*`    |

No inter-service config dependency. Each service reads `config.json` from the project root
(via simple `Path("config.json")` relative path — guaranteed by `start.sh` which `cd`s into
the project root before launching services). No `os.environ` injection — config is read
directly into a Python dict.

## Key Conventions

### Config Live-Reload

`config.json` is re-read on every request via `load_config()` — no server restart needed.
Edit the file and the next request picks up changes immediately. Pattern used in both services:

```python
def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
```

Module-level constants are read once at import time for startup settings (ports, hosts).
All other values (API keys, model names, base URLs) are fetched per-request from `load_config()`.

### Paths

- **No `Path(__file__).resolve().parent.parent.parent` traversal.**
- `start.sh` always `cd`s to the project root before running services.
- All paths use simple relative paths: `Path("config.json")`, `Path("services/gateway/ui")`.

### General

- **Commit messages:** Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, etc.) — lowercase, no period
- **Python:** always use `-B` flag when running Python (prevents `__pycache__`), bytecode disabled via `-B` flag in start.sh (not per-file)
- **Config:** `config.json` file loaded per-request, secrets never served over HTTP (redacted as `***`)
- **HTTP client:** shared `httpx.AsyncClient` attached to `app.state` in lifespan
- **Tests:** always run separately (`pytest services/llm/tests.py` then `pytest services/gateway/tests.py`) — same filenames cause import collisions
- **Auth:** Gateway uses same-origin trust pattern — browser requests trusted automatically, external clients need `X-API-Key` header matching `GATEWAY_API_KEY` in config.json

## LLM Service Details

- Uses **Anthropic-compatible API format**: `POST {base_url}/messages` with `x-api-key` header and `anthropic-version: 2023-06-01`.
- `max_tokens: 4096` is always sent (required by Anthropic API).
- Returns the **full Anthropic response body** — content array may include `thinking` blocks before `text` blocks.
- When `LLM_API_KEY` is empty/unset, returns a placeholder message instead of calling the API.

## Pending / Next Steps

- **Settings UI** — The user's stated goal: "the user should not make any manual changes through the files, the user only use the ui." This means building a Settings page in the frontend + `PUT /api/config` endpoint in the Gateway. Currently config is edited by hand in `config.json`.

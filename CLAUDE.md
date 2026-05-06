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
│   ├── util/
│   │   └── app.py       # Util microservice — manages settings.json CRUD
│   └── llm/
│       ├── app.py       # LLM microservice — DeepSeek API calls via Anthropic format
│       └── tests.py
├── .claude/             # Claude project settings
├── .config/             # Local Claude CLI config (gitignored)
├── config.json          # Infrastructure config / secrets (gitignored)
├── config.example.json  # Config template (tracked)
├── settings.json        # LLM provider settings (gitignored)
├── settings.example.json# Settings template (tracked)
├── CLAUDE.md            # Project memory for Claude
├── CONTRIBUTING.md      # Commit convention guide
├── LICENSE              # MIT license
├── README.md
├── requirements.txt
├── install.sh           # Setup script (venv + deps + config.json, settings.json)
├── start.sh             # Launch services
├── stop.sh              # Stop services
└── restart.sh           # Restart services
```

## Git Status

- **Branch:** `main`
- **Remote:** `origin` → `https://github.com/npminstallpotato/openpotato.git`
- **Latest commit:** `refactor: use simple relative paths, remove Path(__file__) traversal`

## Architecture

Three independent FastAPI microservices. Config is split into two files:

| File | Contents | Read behavior |
|------|----------|--------------|
| `config.json` | `INTERNAL_SECRET`, ports, hosts | **Once at startup** (module level) |
| `settings.json` | `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | **Live-reloaded** on every request |

| Service     | Port | Role                                             |
|-------------|------|--------------------------------------------------|
| **LLM**     | 8002 | Proxies chat requests to DeepSeek API            |
| **Util**    | 8001 | Manages `settings.json` CRUD (read/write/persist) |
| **Gateway** | 8000 | Serves the UI + proxies `/api/llm/*` and `/api/settings` |

No inter-service config dependency. Each service reads files from the project root
(via simple `Path("config.json")` / `Path("settings.json")` relative paths — guaranteed by `start.sh` which `cd`s into
the project root before launching services). No `os.environ` injection — config is read
directly into a Python dict.

## Key Conventions

### Config vs Settings

- **`config.json`** (infrastructure/secrets) — read once at module level. Ports, hosts, internal secret. Changing requires server restart.
- **`settings.json`** (LLM provider config) — live-reloaded on every request via `load_settings()`. Edit the file and the next request picks up changes immediately. Pattern:
  ```python
  def load_settings():
      try:
          with open(SETTINGS_PATH) as f:
              return json.load(f)
      except (FileNotFoundError, json.JSONDecodeError):
          return {}
  ```
- Both files are gitignored (contain real secrets). `config.example.json` and `settings.example.json` are tracked templates.

### Paths

- **No `Path(__file__).resolve().parent.parent.parent` traversal.**
- `start.sh` always `cd`s to the project root before running services.
- All paths use simple relative paths: `Path("config.json")`, `Path("services/gateway/ui")`.

### General

- **Commit messages:** One-line Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, etc.) — lowercase, no period. Always use a single line, never multi-line.
- **Python:** always use `-B` flag when running Python (prevents `__pycache__`), bytecode disabled via `-B` flag in start.sh (not per-file)
- **Config:** `config.json` (infra, read once) + `settings.json` (LLM, live-reloaded), secrets never served over HTTP (redacted as `***`)
- **HTTP client:** shared `httpx.AsyncClient` attached to `app.state` in lifespan
- **Tests:** always run separately (`pytest services/llm/tests.py` then `pytest services/gateway/tests.py`) — same filenames cause import collisions
- **No external auth middleware** — Gateway API routes are open (local-hosted app)
- **Internal service auth** — LLM service only accepts requests with `X-Internal-Secret` header matching `INTERNAL_SECRET` in `config.json`. The Gateway adds this header automatically when proxying.

## LLM Service Details

- Uses **Anthropic-compatible API format**: `POST {base_url}/messages` with `x-api-key` header and `anthropic-version: 2023-06-01`.
- `max_tokens: 4096` is always sent (required by Anthropic API).
- Returns the **full Anthropic response body** — content array may include `thinking` blocks before `text` blocks.
- When `LLM_API_KEY` is empty/unset, returns a placeholder message instead of calling the API.

## Design Conventions

- **Claude Frontend Design approach** — Use warm, amber-toned aesthetic (amber-400 primary, warm-900 sidebar, Sora font). Glassmorphism, soft shadows, subtle gradients, smooth animations. Keep UI feeling premium, cozy, and potato-themed. Always maintain this design language for all new frontend work.

## Pending / Next Steps

- ~~**Settings UI** — The user's stated goal: "the user should not make any manual changes through the files, the user only use the ui." This means building a Settings page in the frontend + `PUT /api/settings` endpoint in the Gateway. Currently settings are edited by hand in `settings.json`.~~ ✅ Done — Settings page with live-reload from Util microservice, `/api/settings` GET/PUT endpoints, and frontend form with save/restore/cancel.

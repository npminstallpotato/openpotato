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
│       ├── app.py       # LLM microservice — DeepSeek API calls
│       └── tests.py
├── .claude/             # Claude project settings
├── .config/             # Local Claude CLI config (gitignored)
├── .env.example         # Environment variable template
├── .env                 # Local env vars with API keys (gitignored)
├── CLAUDE.md            # Project memory for Claude
├── CONTRIBUTING.md      # Commit convention guide
├── LICENSE              # MIT license
├── README.md
├── requirements.txt
├── install.sh           # Setup script (venv + deps + .env)
├── start.sh             # Launch services
└── stop.sh              # Stop services
```

## Git Status

- **Branch:** `main`
- **Remote:** `origin` → `https://github.com/npminstallpotato/openpotato.git`
- **Latest commit:** `feat: scaffold fastapi microservices with gateway, llm, and config service`

## Architecture

Two FastAPI microservices — each self-bootstrapping from `.env` + environment variables:

| Service     | Port | Role                                    |
|-------------|------|-----------------------------------------|
| **LLM**     | 8002 | Proxies chat requests to DeepSeek API   |
| **Gateway** | 8000 | Serves the UI + proxies `/api/llm/*`    |

No inter-service config dependency. Each service loads `.env` via `python-dotenv` at startup,
reads its own config from `os.environ`, and falls back to safe defaults.

## Key Conventions

- **Commit messages:** Conventional Commits (`feat:`, `fix:`, `docs:`, etc.) — lowercase, no period
- **Python:** always use `-B` flag when running Python (prevents `__pycache__`), bytecode disabled via `-B` flag in start.sh (not per-file)
- **Config:** `.env` file loaded via `python-dotenv`, secrets never served over HTTP
- **HTTP client:** shared `httpx.AsyncClient` attached to `app.state` in lifespan
- **Tests:** always run separately (`pytest services/llm/tests.py` then `pytest services/gateway/tests.py`) — same filenames cause import collisions

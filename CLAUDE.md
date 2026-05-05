# OpenPotato 🥔

> AI agents at your command, powered by your preferred LLM — built 100% by AI.
> Updated: 2026-05-05

## Project Structure

```
OpenPotato/
├── apps/
│   ├── gateway/
│   │   ├── app.py       # FastAPI gateway — serves UI + proxies to backends
│   │   └── ui/          # Static frontend (index.html, style.css, app.js)
│   ├── llm/
│   │   ├── app.py       # LLM microservice — proxied DeepSeek API calls
│   │   └── tests.py
│   └── utils/
│       ├── app.py       # Config microservice — reads config.json
│       └── tests.py
├── .claude/             # Claude project settings
├── .config/             # Local Claude CLI config (gitignored)
├── CLAUDE.md            # Project memory for Claude
├── CONTRIBUTING.md      # Commit convention guide
├── LICENSE              # MIT license
├── README.md
├── config-example.json  # Config template (tracked)
├── config.json          # Local config with API keys (gitignored)
├── requirements.txt
├── install.sh           # Setup script (venv + deps + config)
├── start.sh             # Launch all three services
└── stop.sh              # Stop all three services
```

## Git Status

- **Branch:** `main`
- **Remote:** `origin` → `https://github.com/npminstallpotato/openpotato.git`
- **Latest commit:** `feat: scaffold fastapi microservices with gateway, llm, and config service`

## Architecture

Three FastAPI microservices:

| Service   | Port | Role                                      |
|-----------|------|-------------------------------------------|
| **Utils** | 8001 | Centralized config — reads `config.json`  |
| **LLM**   | 8002 | Proxies chat requests to DeepSeek API     |
| **Gateway** | 8000 | Serves the UI + proxies `/api/*` routes   |

Services (except Utils) fetch config from Utils at startup — never read config.json directly.

## Key Conventions

- **Commit messages:** Conventional Commits (`feat:`, `fix:`, `docs:`, etc.) — lowercase, no period
- **Python:** no bytecode (`sys.dont_write_bytecode = True`), no `__pycache__`
- **Config:** all fallbacks are hardcoded defaults, no `os.getenv()`
- **Tests:** each service has `tests.py`, run separately to avoid import conflicts

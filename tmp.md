# OpenPotato — Code Review & Improvement Suggestions

**Repository:** github.com/npminstallpotato/openpotato  
**Overview:** A microservice-based AI agent gateway (Python/FastAPI) with 3 services: gateway (proxy + UI), LLM (DeepSeek wrapper), and utils (config server). Clean, well-structured for a young project (2 commits). Below are suggestions organized by priority.

---

## High Priority — Security

### 1. Config endpoint exposes API key over the network

- `GET /config` returns the *entire* `config.json` including `llm.api_key`. Any process on the machine (or network, since it binds `0.0.0.0`) can read the secret.
- **Fix:** dont use utils, use .env file directly.

### 2. No authentication on any endpoint

- The gateway proxies to LLM services with zero auth. Anyone who can reach port 8000 can run LLM queries on your API key.
- **Fix:** Add at least an API-key middleware for external access. Even a `X-API-Key` header check would help to make sure only this application can access the app endpoint.

### 3. Binding to `0.0.0.0` by default

- All services listen on all interfaces. For a development tool, `127.0.0.1` is safer.
- **Fix:** Default host to `127.0.0.1`; let users opt into `0.0.0.0` via config.

---

## Medium Priority — Architecture & Reliability

### 4. LLM service hardcodes `UTILS_BASE`

- The gateway reads ports from config, but the LLM service has `UTILS_BASE = "http://localhost:8001"` hardcoded. If utils port changes in config, LLM won't find it.
- **Fix:** Have LLM read the utils URL from an env var or accept it as a CLI arg, or read config.json directly for bootstrap.

### 5. No startup ordering / readiness checks in `start.sh`

- LLM fetches config from Utils on startup, but `start.sh` launches them near-simultaneously. If Utils isn't ready, LLM falls back to defaults silently.
- **Fix:** Add a wait-for-healthy loop (e.g., poll `localhost:8001/health`) before starting dependent services, or use a process manager like `supervisord` / `honcho`.

### 6. Config is loaded fresh on every request in utils

- `load_config()` reads and parses `config.json` from disk on every single HTTP request. Fine at low traffic, but adds latency and file I/O.
- **Fix:** Cache config in memory with a TTL or file-watcher, or reload only on `SIGHUP`.

### 7. Gateway creates a new `httpx.AsyncClient` per request

- Each proxy call opens and closes a TCP connection. Connection pooling is lost.
- **Fix:** Create a shared `httpx.AsyncClient` at app startup (in lifespan) and reuse it across requests.

### 8. No graceful shutdown in `stop.sh`

- `kill` sends SIGTERM, which is fine, but there's no wait/timeout before a SIGKILL. Hung processes get orphaned.
- **Fix:** Add a `sleep 3 && kill -9` fallback, or use uvicorn's built-in shutdown signals.

---

## Medium Priority — Developer Experience / Open Source Readiness

### 9. No `pyproject.toml` or packaging

- The project uses only `requirements.txt`. For an open-source Python project, `pyproject.toml` provides metadata, script entrypoints, and better dependency management (with optional extras like `[dev]` for test deps).
- **Fix:** Add a `pyproject.toml` with project metadata, dependencies, and a `[project.scripts]` entrypoint.

### 10. No test runner configuration

- Tests exist but there's no `pytest.ini`, `pyproject.toml [tool.pytest]`, or CI pipeline to run them.
- **Fix:** Add a `pytest` section to `pyproject.toml` and a GitHub Actions workflow (`.github/workflows/test.yml`).

### 11. Gateway has no tests

- LLM and Utils have test files. Gateway (the most complex service) has none.
- **Fix:** Add `apps/gateway/tests.py` covering the proxy logic, error handling (502), and static file serving.

### 12. No `.env` support despite `python-dotenv` in requirements

- `python-dotenv` is listed as a dependency but never imported or used anywhere in the code.
- **Fix:** Either use it (e.g., load `LLM_API_KEY` from `.env` as a safer alternative to `config.json`) or remove the unused dependency.

---

## Low Priority — Code Quality Polish

### 13. `_Config` class uses class-level mutable state

- The pattern works but is unusual and makes testing harder (global state leaks between tests).
- **Fix:** Use a Pydantic `BaseSettings` or a simple dataclass instance attached to `app.state`.

### 14. Gateway config schema mismatch with `config-example.json`

- Gateway expects `config["gateway"]["llm_base"]` and `config["gateway"]["utils_base"]`, but `config-example.json` has no `"gateway"` key. This means the gateway always falls through to defaults.
- **Fix:** Either add `"gateway": {...}` to the example config, or change the gateway to read `llm_port`/`utils_port` and construct URLs itself.

### 15. No versioning / changelog

- For open-source, a `CHANGELOG.md` and semantic versioning help users track what's new.
- **Fix:** Add a changelog and tag releases.

### 16. `sys.dont_write_bytecode = True` repeated in every file

- **Fix:** Set `PYTHONDONTWRITEBYTECODE=1` in the venv activate script or in `start.sh` once.

---

## Summary — Top 3 Most Impactful Changes

| # | What | Why |
|---|------|-----|
| 1 | Redact secrets from `/config` endpoint | Prevents API key leakage |
| 2 | Reuse `httpx.AsyncClient` in gateway | Connection pooling, performance |
| 3 | Add GitHub Actions CI + gateway tests | Catches regressions, builds contributor trust |

The codebase is clean and readable for its age. The architecture is sound (config service, LLM service, gateway). The main gaps are around security hardening and operational robustness — typical for an early-stage project. Solid foundation to build on.
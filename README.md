# OpenPotato 🥔

A team of AI Agents, powered by your preferred LLM — vibe coded entirely.

## Quick Start

```bash
# 1. Install
./install.sh

# 2. Start all services
./start.sh

# 3. Open in browser
open http://localhost:8000
```

## Configuration

After running `./install.sh`, two files control the system:

### `config.json` — Infrastructure / secrets (read once at startup)

| Key | Description |
|-----|-------------|
| `INTERNAL_SECRET` | Shared secret between Gateway and LLM services |
| `HOST` | Host all services bind to (default: `127.0.0.1`) |
| `GATEWAY_PORT` | Port the Gateway serves the UI on |
| `LLM_PORT` | Port the LLM service runs on |
| `UTIL_PORT` | Port the Util (settings) service runs on |

### `settings.json` — LLM provider (live-reloaded, no restart needed)

| Key | Description |
|-----|-------------|
| `LLM_API_KEY` | Your DeepSeek (or compatible) API key |
| `LLM_MODEL` | Model name (default: `deepseek-v4-flash`) |
| `LLM_BASE_URL` | API base URL (default: `https://api.deepseek.com/anthropic`) |

> **Settings can also be edited via the UI** — navigate to the Settings page (sidebar or `Cmd+,`) to view and update these values without editing files directly.

## API Endpoints

All requests go through the **Gateway** (`http://localhost:8000`). The LLM service is not exposed directly.

### Gateway

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the chat UI |
| `GET` | `/api/config` | Returns current config (API key redacted) |
| `GET` | `/api/settings` | Returns LLM provider settings (live-reloaded) |
| `PUT` | `/api/settings` | Updates and persists LLM provider settings |
| `GET` | `/api/settings/defaults` | Returns default settings from `settings.example.json` |
| `*` | `/api/llm/*` | Proxies requests to the LLM service |

### LLM (via Gateway proxy)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/llm/health` | Health check |
| `POST` | `/api/llm/chat` | Send a chat message |
| `GET` | `/api/llm/chat?message=...` | Send a chat message via query param |

**Chat request:**

```json
{ "message": "Hello, world!" }
```

**Chat response (Anthropic message format):**

```json
{
  "id": "msg_01abc123",
  "type": "message",
  "role": "assistant",
  "content": [
    { "type": "text", "text": "Hello! How can I help you today?" }
  ],
  "stop_reason": "end_turn"
}
```

## Project Structure

```
├── services/
│   ├── gateway/
│   │   ├── app.py       # FastAPI gateway — serves UI + proxies to LLM
│   │   ├── tests.py      # Gateway tests
│   │   └── ui/          # Static frontend files
│   │       ├── index.html
│   │       ├── style.css
│   │       └── app.js
│   ├── util/
│   │   └── app.py       # Util microservice — manages settings.json
│   └── llm/
│       ├── app.py       # LLM microservice — DeepSeek integration
│       └── tests.py
├── config.json              # Infrastructure config / secrets (gitignored)
├── config.example.json      # Config template
├── settings.json            # LLM provider settings (gitignored)
├── settings.example.json    # Settings template
├── install.sh               # One-shot setup script
├── start.sh                 # Start all services
├── stop.sh                  # Stop all services
├── restart.sh               # Restart all services
└── requirements.txt      # Python dependencies
```

---

[MIT License](LICENSE) · [Contributing](CONTRIBUTING.md)

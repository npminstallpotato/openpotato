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

After running `./install.sh`, edit `config.json` with your settings:

| Key | Description |
|-----|-------------|
| `LLM_API_KEY` | Your DeepSeek (or compatible) API key |
| `LLM_MODEL` | Model name (default: `deepseek-v4-flash`) |
| `LLM_BASE_URL` | API base URL (default: `https://api.deepseek.com/anthropic`) |
| `LLM_PORT` | Port the LLM service runs on |
| `GATEWAY_PORT` | Port the Gateway serves the UI on |
| `LLM_HOST` | Host the LLM service binds to (default: `127.0.0.1`) |
| `GATEWAY_HOST` | Host the Gateway binds to (default: `127.0.0.1`) |

## API Endpoints

All requests go through the **Gateway** (`http://localhost:8000`). The LLM service is not exposed directly.

### Gateway

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the chat UI |
| `GET` | `/api/config` | Returns current config (API key redacted) |
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
│   └── llm/
│       ├── app.py       # LLM microservice — DeepSeek integration
│       └── tests.py
├── config.json          # Local config with API keys (gitignored)
├── config.example.json  # Configuration template
├── install.sh            # One-shot setup script
├── start.sh              # Start all services
├── stop.sh               # Stop all services
└── requirements.txt      # Python dependencies
```

---

[MIT License](LICENSE) · [Contributing](CONTRIBUTING.md)

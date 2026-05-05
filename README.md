# OpenPotato 🥔

A team of AI Agents, powered by your preferred LLM — built entirely by AI.

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

Edit `config.json` with your settings:

```json
{
  "llm": {
    "api_key": "sk-...",
    "model": "deepseek-v4-flash",
    "base_url": "https://api.deepseek.com/v1"
  },
  "llm_port": 8002,
  "utils_port": 8001,
  "gateway_port": 8000
}
```

| Key | Description |
|-----|-------------|
| `llm.api_key` | Your DeepSeek (or compatible) API key |
| `llm.model` | Model name (default: `deepseek-v4-flash`) |
| `llm.base_url` | API base URL (default: `https://api.deepseek.com/v1`) |
| `llm_port` | Port the LLM service runs on |
| `utils_port` | Port the Utils config service runs on |
| `gateway_port` | Port the Gateway serves the UI on |

## Project Structure

```
├── apps/
│   ├── gateway/
│   │   ├── app.py       # FastAPI gateway — serves UI + proxies
│   │   └── ui/          # Static frontend files
│   │       ├── index.html
│   │       ├── style.css
│   │       └── app.js
│   ├── llm/
│   │   ├── app.py       # LLM microservice — DeepSeek integration
│   │   └── tests.py
│   └── utils/
│       ├── app.py       # Config microservice — reads config.json
│       └── tests.py
├── config-example.json  # Example config (template)
├── config.json          # Local config (git-ignored)
├── install.sh           # One-shot setup script
├── start.sh             # Start all three services
├── stop.sh              # Stop all three services
└── requirements.txt     # Python dependencies
```

## Requirements

- **Python 3.10+**

#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/npminstallpotato/openpotato.git}"
INSTALL_DIR="${INSTALL_DIR:-openpotato}"

# ── Colors ───────────────────────────────────────────────────────────────────
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}OpenPotato — Installer${NC}"
echo

# ── Clone repo if not already in one ─────────────────────────────────────────

if [ -d "services" ] && [ -f "requirements.txt" ]; then
    echo "Already in OpenPotato repository."
else
    command -v git >/dev/null 2>&1 || { echo -e "${RED}Error: git is required${NC}"; exit 1; }
    if [ ! -d "$INSTALL_DIR" ]; then
        echo "Cloning OpenPotato into ./$INSTALL_DIR …"
        git clone --quiet "$REPO_URL" "$INSTALL_DIR"
        echo -e "${GREEN}✓ Cloned into ./$INSTALL_DIR${NC}"
    else
        echo -e "${YELLOW}Found existing ./$INSTALL_DIR — using it.${NC}"
    fi
    cd "$INSTALL_DIR"
fi

echo

# ── Check / install Python ───────────────────────────────────────────────────

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        version="$("$candidate" --version 2>&1 | awk '{print $2}' | cut -d. -f1-2)"
        major="${version%.*}"
        minor="${version#*.}"
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${YELLOW}Python 3.10+ not found — attempting to install via Homebrew…${NC}"
    if ! command -v brew &>/dev/null; then
        echo -e "${RED}Homebrew not found. Install it first:${NC}"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    brew install python@3.13
    # Re-check after install
    for candidate in python3 python; do
        if command -v "$candidate" &>/dev/null; then
            version="$("$candidate" --version 2>&1 | awk '{print $2}' | cut -d. -f1-2)"
            major="${version%.*}"
            minor="${version#*.}"
            if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                PYTHON="$candidate"
                break
            fi
        fi
    done
fi

if [ -z "$PYTHON" ]; then
    echo -e "${RED}Error: Python 3.10+ is required but not found.${NC}"
    echo "Install Python from https://www.python.org/downloads/ and try again."
    exit 1
fi

echo -e "  Python:  $($PYTHON --version)"
echo

# ── Create virtual environment ───────────────────────────────────────────────

if [ -d ".venv" ]; then
    echo -e "${YELLOW}Found existing virtual environment (.venv). Skipping creation.${NC}"
else
    echo "Creating virtual environment…"
    "$PYTHON" -m venv .venv
    echo -e "${GREEN}✓ Created .venv${NC}"
fi

echo

# ── Install dependencies ─────────────────────────────────────────────────────

echo "Installing dependencies…"
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo

# ── Create config.json from example (if missing) ──────────────────────────

if [ -f "config.json" ]; then
    echo -e "${YELLOW}config.json already exists — keeping it as-is.${NC}"
else
    if [ -f "config.example.json" ]; then
        cp config.example.json config.json
        echo -e "${GREEN}✓ Created config.json from config.example.json${NC}"
    else
        echo -e "${YELLOW}Warning: config.example.json not found — skipping config setup.${NC}"
    fi
fi

echo

# ── Summary ───────────────────────────────────────────────────────────────────

echo -e "${BOLD}Installation complete!${NC}"
echo
echo -e "  ${GREEN}▶${NC} Start all services:     ${BOLD}./start.sh${NC}"
echo -e "  ${GREEN}▶${NC} Open in browser:        ${BOLD}http://localhost:8000${NC}"
echo -e "  ${GREEN}▶${NC} Stop all services:      ${BOLD}./stop.sh${NC}"
echo

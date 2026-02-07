#!/usr/bin/env bash
# Sets up the MA development environment and symlinks the MSX Bridge provider.
# Usage: ./scripts/link-to-ma.sh [/path/to/ma-server]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MA_SERVER="${1:-$PROJECT_ROOT/../ma-server}"

PROVIDER_SRC="$PROJECT_ROOT/provider/msx_bridge"
PROVIDER_DST="$MA_SERVER/music_assistant/providers/msx_bridge"

if [ ! -d "$MA_SERVER/music_assistant/providers" ]; then
    echo "Error: MA server not found at $MA_SERVER"
    echo "Usage: $0 [/path/to/music-assistant-server]"
    exit 1
fi

if [ ! -d "$PROVIDER_SRC" ]; then
    echo "Error: Provider source not found at $PROVIDER_SRC"
    exit 1
fi

# --- Set up MA venv if needed ---
if [ ! -d "$MA_SERVER/.venv" ]; then
    echo "Setting up MA development environment..."
    bash "$MA_SERVER/scripts/setup.sh"
fi

# --- Symlink provider ---
if [ -e "$PROVIDER_DST" ]; then
    echo "Removing existing link/directory at $PROVIDER_DST"
    rm -rf "$PROVIDER_DST"
fi

ln -s "$PROVIDER_SRC" "$PROVIDER_DST"
echo "Linked: $PROVIDER_SRC -> $PROVIDER_DST"

# --- Verify imports ---
echo ""
echo "Verifying provider imports..."
if "$MA_SERVER/.venv/bin/python" -c "from music_assistant.providers.msx_bridge import setup" 2>/dev/null; then
    echo "OK: Provider imports successfully"
else
    echo "WARNING: Provider import failed — check for errors"
fi

echo ""
echo "=== Ready ==="
echo "Activate venv:  source $MA_SERVER/.venv/bin/activate"
echo "Run server:     python -m music_assistant --log-level debug"
echo "Run tests:      pytest"
echo "Pre-commit:     pre-commit run --all-files"

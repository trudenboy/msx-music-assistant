#!/usr/bin/env bash
# Start/stop the MA development server for local testing.
#
# Usage:
#   ./scripts/test-server.sh start   # start in background
#   ./scripts/test-server.sh stop    # stop background server
#   ./scripts/test-server.sh status  # check if running
#   ./scripts/test-server.sh log     # tail the server log
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MA_SERVER="${MA_SERVER:-$PROJECT_ROOT/../ma-server}"
DATA_DIR="${MA_DATA_DIR:-$HOME/.musicassistant}"
PID_FILE="$PROJECT_ROOT/.test-server.pid"
LOG_FILE="$PROJECT_ROOT/.test-server.log"

_require_venv() {
    if [ ! -d "$MA_SERVER/.venv" ]; then
        echo "Error: MA venv not found. Run ./scripts/link-to-ma.sh first."
        exit 1
    fi
}

_is_running() {
    [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

cmd_start() {
    if _is_running; then
        echo "Server already running (PID $(cat "$PID_FILE"))"
        return 0
    fi
    _require_venv

    echo "Starting MA server..."
    # shellcheck disable=SC1091
    source "$MA_SERVER/.venv/bin/activate"
    cd "$MA_SERVER"
    python -m music_assistant --log-level debug \
        > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_FILE"
    cd "$PROJECT_ROOT"

    # Wait briefly and verify it didn't crash
    sleep 2
    if _is_running; then
        echo "Server started (PID $pid)"
        echo "Log: $LOG_FILE"
        echo "Data: $DATA_DIR"
    else
        echo "Server failed to start. Check log:"
        tail -20 "$LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

cmd_stop() {
    if ! _is_running; then
        echo "Server not running"
        rm -f "$PID_FILE"
        return 0
    fi
    local pid
    pid="$(cat "$PID_FILE")"
    echo "Stopping server (PID $pid)..."
    kill "$pid"
    # Wait up to 5s for graceful shutdown
    for _ in $(seq 1 10); do
        if ! kill -0 "$pid" 2>/dev/null; then
            break
        fi
        sleep 0.5
    done
    # Force kill if still running
    if kill -0 "$pid" 2>/dev/null; then
        echo "Force killing..."
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
    echo "Server stopped"
}

cmd_status() {
    if _is_running; then
        echo "Running (PID $(cat "$PID_FILE"))"
    else
        echo "Not running"
        rm -f "$PID_FILE"
    fi
}

cmd_log() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "No log file found"
        return 1
    fi
    tail -f "$LOG_FILE"
}

case "${1:-}" in
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    log)    cmd_log ;;
    *)
        echo "Usage: $0 {start|stop|status|log}"
        exit 1
        ;;
esac

#!/bin/bash
# Website control script
# Usage: ./website.sh [start|stop|restart|status]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WEBSITE_DIR="$SCRIPT_DIR/website"
LOG_FILE="$WEBSITE_DIR/logs/website.log"
PID_FILE="$WEBSITE_DIR/.pid"

# Load environment variables from .env if present
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    . "$SCRIPT_DIR/.env"
    set +a
fi

start_website() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Website already running (PID $(cat "$PID_FILE"))"
        return 1
    fi
    cd "$WEBSITE_DIR"
    mkdir -p logs
    if [ -f "venv/bin/python3" ]; then
        PYTHON="venv/bin/python3"
    else
        PYTHON="python3"
    fi
    $PYTHON app.py >> "$LOG_FILE" 2>&1 &
    local pid=$!
    # See server.sh: `&` reports a fork, not a successful start, and the child's
    # error goes to the log rather than the terminal. Verify it is still alive
    # before claiming it started.
    sleep 1
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "Website failed to start. Last lines of $LOG_FILE:" >&2
        tail -n 10 "$LOG_FILE" >&2
        return 1
    fi
    echo "$pid" > "$PID_FILE"
    echo "Website started (PID $pid)"
}

stop_website() {
    if [ ! -f "$PID_FILE" ]; then
        local pid=$(pgrep -f "python.*website.*app.py")
        if [ -n "$pid" ]; then
            kill "$pid"
            echo "Website stopped (PID $pid)"
            return 0
        fi
        echo "Website not running"
        return 1
    fi
    local pid=$(cat "$PID_FILE")
    if kill "$pid" 2>/dev/null; then
        rm -f "$PID_FILE"
        echo "Website stopped (PID $pid)"
    else
        rm -f "$PID_FILE"
        echo "Website not running (stale PID file removed)"
    fi
}

status_website() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Website running (PID $(cat "$PID_FILE"))"
    else
        local pid=$(pgrep -f "python.*website.*app.py")
        if [ -n "$pid" ]; then
            echo "Website running (PID $pid, no PID file)"
        else
            echo "Website not running"
        fi
    fi
}

case "${1:-start}" in
    start)   start_website ;;
    stop)    stop_website ;;
    restart) stop_website; sleep 1; start_website ;;
    status)  status_website ;;
    *)       echo "Usage: $0 [start|stop|restart|status]"; exit 1 ;;
esac

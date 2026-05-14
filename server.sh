#!/bin/bash
# Compunet server control script
# Usage: ./server.sh [start|stop|restart|status]

SERVER_DIR="$(dirname "$0")/server"
LOG_FILE="$(dirname "$0")/server/logs/compunet-server.log"
PID_FILE="$(dirname "$0")/server/.pid"

start_server() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Server already running (PID $(cat "$PID_FILE"))"
        return 1
    fi
    cd "$SERVER_DIR"
    mkdir -p logs
    python3 compunet_server.py >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Server started (PID $!)"
}

stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        local pid=$(pgrep -f compunet_server.py)
        if [ -n "$pid" ]; then
            kill "$pid"
            echo "Server stopped (PID $pid)"
            return 0
        fi
        echo "Server not running"
        return 1
    fi
    local pid=$(cat "$PID_FILE")
    if kill "$pid" 2>/dev/null; then
        rm -f "$PID_FILE"
        echo "Server stopped (PID $pid)"
    else
        rm -f "$PID_FILE"
        echo "Server not running (stale PID file removed)"
    fi
}

status_server() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Server running (PID $(cat "$PID_FILE"))"
    else
        local pid=$(pgrep -f compunet_server.py)
        if [ -n "$pid" ]; then
            echo "Server running (PID $pid, no PID file)"
        else
            echo "Server not running"
        fi
    fi
}

case "${1:-start}" in
    start)   start_server ;;
    stop)    stop_server ;;
    restart) stop_server; sleep 1; start_server ;;
    status)  status_server ;;
    *)       echo "Usage: $0 [start|stop|restart|status]"; exit 1 ;;
esac

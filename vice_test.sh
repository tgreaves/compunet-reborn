#!/bin/bash
# Compunet Reborn — Automated VICE test launcher
# Launches x64sc with the client PRG, injects keystrokes to automate login.
# Leaves remote monitor open on port 6510 for debug sessions.
#
# Usage: ./test.sh <ip_address> <username> <password> [--restart-server]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PRG="$SCRIPT_DIR/client/c64/compunet-reborn.prg"
MONITOR_PORT=6510
VICE=x64sc

# --- Parse arguments ---

RESTART_SERVER=false

args=()
for arg in "$@"; do
    if [ "$arg" = "--restart-server" ]; then
        RESTART_SERVER=true
    else
        args+=("$arg")
    fi
done

if [ ${#args[@]} -ne 3 ]; then
    echo "Usage: $0 <ip_address> <username> <password> [--restart-server]"
    exit 1
fi

IP_ADDRESS="${args[0]}"
USERNAME="${args[1]}"
PASSWORD="${args[2]}"

# --- Preflight checks ---

if [ ! -f "$PRG" ]; then
    echo "Error: PRG not found at $PRG"
    echo "Build it first: make -C client/c64/src/"
    exit 1
fi

if ! command -v "$VICE" &>/dev/null; then
    echo "Error: $VICE not found in PATH"
    exit 1
fi

# --- Optionally restart server ---

if [ "$RESTART_SERVER" = true ]; then
    echo "Restarting server..."
    "$SCRIPT_DIR/server.sh" restart
    sleep 1
fi

# --- Kill any existing VICE processes ---

if pkill -x "$VICE" 2>/dev/null; then
    echo "Killed existing $VICE process(es)."
    sleep 1
fi

# --- Launch VICE ---

echo "Launching $VICE with remote monitor on port $MONITOR_PORT..."
echo "  PRG:      $PRG"
echo "  Server:   $IP_ADDRESS"
echo "  Username: $USERNAME"

$VICE \
    -remotemonitor \
    -remotemonitoraddress ip4://127.0.0.1:$MONITOR_PORT \
    "$PRG" &

VICE_PID=$!
echo "  VICE PID: $VICE_PID"

# --- Wait for remote monitor to become available ---

echo "Waiting for remote monitor..."
for i in $(seq 1 30); do
    if nc -z 127.0.0.1 $MONITOR_PORT 2>/dev/null; then
        echo "Remote monitor ready."
        break
    fi
    if ! kill -0 $VICE_PID 2>/dev/null; then
        echo "Error: VICE exited unexpectedly"
        exit 1
    fi
    sleep 0.5
done

if ! nc -z 127.0.0.1 $MONITOR_PORT 2>/dev/null; then
    echo "Error: remote monitor did not become available"
    kill $VICE_PID 2>/dev/null
    exit 1
fi

send_keybuf() {
    local text
    text=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    echo "keybuf $text\\n" | nc -q 1 127.0.0.1 $MONITOR_PORT >/dev/null 2>&1 \
        || echo "keybuf $text\\n" | nc -w 1 127.0.0.1 $MONITOR_PORT >/dev/null 2>&1
}

# --- Inject login sequence ---
# All keystrokes sent via remote monitor for consistent behaviour.

# Step 1: SYS 33184 (after PRG loads and READY. prompt appears)
sleep 3
echo "Sending: SYS 33184"
send_keybuf "SYS 33184"

# Step 2: CONNECT command (after SYS 33184 returns to READY.)
sleep 3
echo "Sending: CONNECT"
send_keybuf "CONNECT"

# Step 3: IP address (phone number prompt)
sleep 2
echo "Sending: $IP_ADDRESS"
send_keybuf "$IP_ADDRESS"

# Step 4: Username
sleep 2
echo "Sending: $USERNAME"
send_keybuf "$USERNAME"

# Step 5: Password (sent char-by-char as the input routine drains the buffer quickly)
sleep 2
echo "Sending: $PASSWORD"
local_pass=$(echo "$PASSWORD" | tr '[:upper:]' '[:lower:]')
for (( i=0; i<${#local_pass}; i++ )); do
    char="${local_pass:$i:1}"
    echo "keybuf $char" | nc -q 1 127.0.0.1 $MONITOR_PORT >/dev/null 2>&1 \
        || echo "keybuf $char" | nc -w 1 127.0.0.1 $MONITOR_PORT >/dev/null 2>&1
    sleep 0.3
done
send_keybuf ""

echo ""
echo "Login sequence complete."
echo "Remote monitor available at: nc 127.0.0.1 $MONITOR_PORT"
echo "VICE PID: $VICE_PID"

wait $VICE_PID 2>/dev/null

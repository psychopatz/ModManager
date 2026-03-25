#!/bin/bash
# Start All (Backend & Frontend) Script

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

kill_port() {
	local port="$1"
	local pids=""

	if command -v lsof >/dev/null 2>&1; then
		pids=$(lsof -ti tcp:"$port")
	elif command -v fuser >/dev/null 2>&1; then
		pids=$(fuser -n tcp "$port" 2>/dev/null)
	fi

	if [ -n "$pids" ]; then
		echo "Stopping process(es) on port $port: $pids"
		kill $pids 2>/dev/null || true
		sleep 1
		kill -9 $pids 2>/dev/null || true
	fi
}

# Clean up old listeners first to avoid address conflicts on restart.
kill_port 8000
kill_port 5173

echo "Starting Backend and Frontend..."

# Run backend in background
"$SCRIPT_DIR/start_backend.sh" &
BACKEND_PID=$!

# Run frontend
"$SCRIPT_DIR/start_frontend.sh"

# When frontend stops, kill backend too
kill $BACKEND_PID

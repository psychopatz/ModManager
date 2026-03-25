#!/bin/bash
# Start Frontend Script

cd "$(dirname "$0")/frontend" || exit

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

# Ensure the default Vite dev-server port is free before starting.
kill_port 5173

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Starting Frontend..."
npm run dev

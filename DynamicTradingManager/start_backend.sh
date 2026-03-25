#!/bin/bash
# Start Backend Script

cd "$(dirname "$0")/backend" || exit

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

# Ensure the backend port is free before starting uvicorn.
kill_port 8000

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

echo "Starting Backend..."
./venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

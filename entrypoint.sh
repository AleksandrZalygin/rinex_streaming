#!/bin/bash
set -e

# Change to src/rnx_streamer directory where all Python files are located
cd /app/src/rnx_streamer

# Function to handle shutdown
shutdown() {
    echo "Shutting down services..."
    kill $API_PID $SCHEDULER_PID 2>/dev/null || true
    wait
    exit 0
}

# Trap SIGTERM and SIGINT
trap shutdown SIGTERM SIGINT

# Determine which service to run based on SERVICE_NAME environment variable
if [ "$SERVICE_NAME" = "api" ]; then
    echo "Starting API server..."
    exec uvicorn API_server:app --host 0.0.0.0 --port 8000
elif [ "$SERVICE_NAME" = "scheduler" ]; then
    echo "Starting Scheduler..."
    exec python3 scheduler.py
else
    # Default: run both services (for standalone Docker run)
    echo "Starting both API server and Scheduler..."

    # Start API server in background
    uvicorn API_server:app --host 0.0.0.0 --port 8000 &
    API_PID=$!
    echo "API server started with PID $API_PID"

    # Wait a bit for API to start
    sleep 3

    # Start Scheduler in background
    python3 scheduler.py &
    SCHEDULER_PID=$!
    echo "Scheduler started with PID $SCHEDULER_PID"

    # Wait for both processes
    wait $API_PID $SCHEDULER_PID
fi

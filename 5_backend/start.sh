#!/bin/bash
# Credit Risk Platform - Backend Startup Script

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export API_HOST="${API_HOST:-0.0.0.0}"
export API_PORT="${API_PORT:-8000}"

echo "=================================================="
echo "Credit Risk Platform - Backend API"
echo "=================================================="
echo ""
echo "Starting server on ${API_HOST}:${API_PORT}"
echo ""

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo "[ERROR] uvicorn not found. Installing..."
    pip install uvicorn[standard]
fi

# Start the server
cd "$(dirname "$0")"
uvicorn main:app --host "${API_HOST}" --port "${API_PORT}" --reload

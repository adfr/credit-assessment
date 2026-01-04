#!/bin/bash
# Credit Risk Platform - Frontend Startup Script

echo "=================================================="
echo "Credit Risk Platform - Frontend"
echo "=================================================="
echo ""

# Set environment variables
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

echo "API URL: ${NEXT_PUBLIC_API_URL}"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "[INFO] Installing dependencies..."
    npm install
fi

# Check if .next exists (build)
if [ ! -d ".next" ]; then
    echo "[INFO] Building application..."
    npm run build
fi

# Start the server
echo "[INFO] Starting Next.js server..."
npm run start

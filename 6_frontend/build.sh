#!/bin/bash
# Credit Risk Platform - Frontend Build Script

echo "=================================================="
echo "Credit Risk Platform - Frontend Build"
echo "=================================================="
echo ""

# Install dependencies
echo "[INFO] Installing dependencies..."
npm install

# Build the application
echo "[INFO] Building Next.js application..."
npm run build

echo ""
echo "[SUCCESS] Build completed!"
echo "Output: .next/"

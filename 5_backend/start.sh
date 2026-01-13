#!/usr/bin/env python3
"""
Credit Risk Platform - Backend Startup Script
"""

import os
import sys
from pathlib import Path

# Get project root from environment or current working directory
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))

# Set up paths
backend_dir = PROJECT_ROOT / "5_backend"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

# Configuration
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))

print("=" * 50)
print("Credit Risk Platform - Backend API")
print("=" * 50)
print()
print(f"Starting server on {API_HOST}:{API_PORT}")
print()

# Import and run uvicorn
import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        reload=False
    )

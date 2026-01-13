#!/usr/bin/env python3
"""
Credit Risk Platform - Backend Startup Script
Works in both Jupyter/CML notebooks and as standalone script.
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

# Import uvicorn and app
import uvicorn
from main import app

# Check if we're in a Jupyter/IPython environment with running event loop
def is_notebook():
    try:
        from IPython import get_ipython
        if get_ipython() is not None:
            return True
    except:
        pass
    return False

if __name__ == "__main__":
    if is_notebook():
        # In Jupyter: use nest_asyncio to allow nested event loops
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            print("[INFO] Installing nest_asyncio for Jupyter compatibility...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "nest_asyncio"])
            import nest_asyncio
            nest_asyncio.apply()

        # Run with nest_asyncio patched loop
        uvicorn.run(app, host=API_HOST, port=API_PORT, reload=False)
    else:
        # Standard execution
        uvicorn.run(app, host=API_HOST, port=API_PORT, reload=False)

#!/usr/bin/env python3
"""
Credit Risk Platform - Backend Startup Script
Works in both Jupyter/CML notebooks and as standalone script.
"""

import os
import sys
from pathlib import Path

# Check if we're in a Jupyter/IPython environment - must be done FIRST
def is_notebook():
    try:
        from IPython import get_ipython
        if get_ipython() is not None:
            return True
    except:
        pass
    return False

# Apply nest_asyncio BEFORE importing uvicorn if in notebook
if is_notebook():
    try:
        import nest_asyncio
        nest_asyncio.apply()
        print("[INFO] Applied nest_asyncio for Jupyter compatibility")
    except ImportError:
        print("[INFO] Installing nest_asyncio...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "nest_asyncio"])
        import nest_asyncio
        nest_asyncio.apply()
        print("[INFO] Applied nest_asyncio for Jupyter compatibility")

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

# Import uvicorn and app AFTER nest_asyncio is applied
import uvicorn
from main import app

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT, reload=False)

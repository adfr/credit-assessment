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

# Configuration - use CML environment variables if available
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("CDSW_APP_PORT", os.environ.get("CDSW_READONLY_PORT", "8090")))

print("=" * 50)
print("Credit Risk Platform - Backend API")
print("=" * 50)
print()
print(f"Starting server on {API_HOST}:{API_PORT}")
print()

# Import uvicorn and app
import uvicorn
from main import app

# Check if we're in a Jupyter/IPython environment
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
        # In Jupyter: run uvicorn in a background thread
        import threading

        config = uvicorn.Config(app, host=API_HOST, port=API_PORT, log_level="info")
        server = uvicorn.Server(config)

        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        print(f"\n[INFO] Server running in background thread")
        print(f"[INFO] API available at http://{API_HOST}:{API_PORT}")
        print(f"[INFO] Docs available at http://{API_HOST}:{API_PORT}/docs")
    else:
        # Standard execution
        uvicorn.run(app, host=API_HOST, port=API_PORT, reload=False)

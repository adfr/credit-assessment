#!/usr/bin/env python3
"""
Credit Risk Platform - Frontend Startup Script
"""

import os
import sys
import subprocess
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))
frontend_dir = PROJECT_ROOT / "6_frontend"
os.chdir(frontend_dir)

# Configuration - use CML environment variables
API_PORT = os.environ.get("CDSW_APP_PORT", os.environ.get("CDSW_READONLY_PORT", "8090"))
API_URL = os.environ.get("NEXT_PUBLIC_API_URL", f"http://127.0.0.1:{API_PORT}")
os.environ["NEXT_PUBLIC_API_URL"] = API_URL

# Frontend port (different from API)
FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "3000")

print("=" * 50)
print("Credit Risk Platform - Frontend")
print("=" * 50)
print()
print(f"API URL: {API_URL}")
print(f"Frontend Port: {FRONTEND_PORT}")
print()

# Check for nvm and node
def run_with_nvm(cmd):
    """Run command with nvm environment."""
    nvm_script = f'''
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    cd {frontend_dir}
    {cmd}
    '''
    return subprocess.run(["bash", "-c", nvm_script], cwd=frontend_dir)

# Check if node_modules exists
if not (frontend_dir / "node_modules").exists():
    print("[INFO] Installing dependencies...")
    run_with_nvm("npm install")

# Check if .next/BUILD_ID exists (means build completed successfully)
build_id_file = frontend_dir / ".next" / "BUILD_ID"
if not build_id_file.exists():
    print("[INFO] Building application (this may take a few minutes)...")
    # Remove incomplete .next directory if it exists
    next_dir = frontend_dir / ".next"
    if next_dir.exists():
        import shutil
        shutil.rmtree(next_dir)
        print("[INFO] Removed incomplete .next directory")
    run_with_nvm("npm run build")

# Start the server
print("[INFO] Starting Next.js server...")
run_with_nvm(f"PORT={FRONTEND_PORT} npm run start")

#!/usr/bin/env python3
"""
Credit Risk Platform - Frontend Startup Script
"""

import os
import sys
import subprocess
import shutil
import socket
import time
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))
frontend_dir = PROJECT_ROOT / "6_frontend"
os.chdir(frontend_dir)

# Configuration - use CML environment variables
# CML Applications must listen on CDSW_APP_PORT for health checks to pass

def get_api_url():
    """Get or construct the API URL for the backend."""
    # First check if explicitly set
    api_url = os.environ.get("NEXT_PUBLIC_API_URL", "")
    if api_url:
        return api_url

    # Try to construct from CML environment
    cdsw_domain = os.environ.get("CDSW_DOMAIN", "")
    cdsw_project = os.environ.get("CDSW_PROJECT", "")

    if cdsw_domain:
        # CML application URL pattern: https://<subdomain>.<domain>
        # Backend subdomain is 'credit-api' as defined in project-metadata.yaml
        backend_subdomain = "credit-api"
        api_url = f"https://{backend_subdomain}.{cdsw_domain}/api"
        return api_url

    # Fallback for local development
    return "http://localhost:8000/api"

API_URL = get_api_url()
os.environ["NEXT_PUBLIC_API_URL"] = API_URL

# Use CDSW_APP_PORT as required by CML - must use env var, not hardcoded
FRONTEND_PORT = os.environ.get("CDSW_APP_PORT")
if not FRONTEND_PORT:
    print("[ERROR] CDSW_APP_PORT not set. This script must run as a CML Application.")
    sys.exit(1)

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
        shutil.rmtree(next_dir)
        print("[INFO] Removed incomplete .next directory")
    run_with_nvm("npm run build")

# Copy static files to standalone directory (required for standalone mode)
standalone_dir = frontend_dir / ".next" / "standalone"
if standalone_dir.exists():
    # Copy static files
    static_src = frontend_dir / ".next" / "static"
    static_dst = standalone_dir / ".next" / "static"
    if static_src.exists() and not static_dst.exists():
        print("[INFO] Copying static files to standalone directory...")
        shutil.copytree(static_src, static_dst)

    # Copy public folder
    public_src = frontend_dir / "public"
    public_dst = standalone_dir / "public"
    if public_src.exists() and not public_dst.exists():
        print("[INFO] Copying public files to standalone directory...")
        shutil.copytree(public_src, public_dst)

# Check if port is available on 127.0.0.1 (where we'll bind)
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', int(port)))
            return False
        except OSError:
            return True

if is_port_in_use(FRONTEND_PORT):
    print(f"[WARN] Port {FRONTEND_PORT} is in use on 127.0.0.1, attempting to free it...")
    subprocess.run(["bash", "-c", f"fuser -k {FRONTEND_PORT}/tcp 2>/dev/null || true"])
    subprocess.run(["bash", "-c", "pkill -9 -f 'node.*server.js' 2>/dev/null || true"])
    time.sleep(2)

# Start the server using standalone mode
# Bind to 127.0.0.1 as per Cloudera documentation - CML proxy handles external access
print("[INFO] Starting Next.js server (standalone mode)...")
print(f"[INFO] Binding to 127.0.0.1:{FRONTEND_PORT}")
run_with_nvm(f"HOSTNAME=127.0.0.1 PORT={FRONTEND_PORT} node .next/standalone/server.js")

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

    # Check if .env.local exists (written by configure_frontend.py)
    env_local = frontend_dir / ".env.local"
    if env_local.exists():
        with open(env_local) as f:
            for line in f:
                if line.startswith("NEXT_PUBLIC_API_URL="):
                    api_url = line.strip().split("=", 1)[1]
                    if api_url:
                        print(f"[INFO] Using API URL from .env.local: {api_url}")
                        return api_url

    # Try to query CML API for actual backend subdomain
    cdsw_domain = os.environ.get("CDSW_DOMAIN", "")
    project_id = os.environ.get("CDSW_PROJECT_ID", "")

    if cdsw_domain and project_id:
        try:
            import cmlapi
            client = cmlapi.default_client()
            apps = client.list_applications(project_id=project_id)

            # Find the Credit Risk API application
            api_apps = [app for app in apps.applications if app.subdomain.startswith("credit-api")]
            if api_apps:
                # Sort by name to get latest version
                api_apps.sort(key=lambda a: a.name, reverse=True)
                subdomain = api_apps[0].subdomain
                api_url = f"https://{subdomain}.{cdsw_domain}/api"
                print(f"[INFO] Found backend app via CML API: {api_apps[0].name} -> {api_url}")
                return api_url
        except Exception as e:
            print(f"[WARN] Could not query CML API: {e}")

        # Fallback to simple pattern (may not work if subdomain has suffix)
        backend_subdomain = "credit-api"
        api_url = f"https://{backend_subdomain}.{cdsw_domain}/api"
        print(f"[WARN] Using default subdomain pattern: {api_url}")
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

# Check if node_modules exists and has required dependencies
# We check for typescript specifically since it's needed for the build
# and was a common cause of "Module not found" errors when node_modules is incomplete
node_modules_dir = frontend_dir / "node_modules"
typescript_dir = node_modules_dir / "typescript"

if not node_modules_dir.exists() or not typescript_dir.exists():
    print("[INFO] Installing dependencies...")
    run_with_nvm("npm install")
else:
    # Even if node_modules exists, run npm install to ensure all deps are up-to-date
    # This is fast when deps are already installed (npm checks package-lock.json)
    print("[INFO] Verifying dependencies...")
    run_with_nvm("npm install --prefer-offline")

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

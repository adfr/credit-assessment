#!/usr/bin/env python3
"""
Install Dependencies Script
Installs Python packages and verifies the installation.
For CML deployment, Node.js installation is handled separately.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n{'='*60}")
    print(f"[INFO] {description}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(f"[WARN] {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed with exit code {e.returncode}")
        print(f"[ERROR] stdout: {e.stdout}")
        print(f"[ERROR] stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"[ERROR] Command not found: {command[0]}")
        return False


def install_python_packages():
    """Install Python packages from requirements.txt."""
    project_root = Path(__file__).parent.parent
    requirements_file = project_root / "requirements.txt"

    if not requirements_file.exists():
        print(f"[ERROR] Requirements file not found: {requirements_file}")
        return False

    # Upgrade pip first
    run_command(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        "Upgrading pip"
    )

    # Install requirements
    return run_command(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
        f"Installing Python packages from {requirements_file}"
    )


def verify_python_packages():
    """Verify critical Python packages are installed."""
    print("\n" + "="*60)
    print("[INFO] Verifying Python package installations")
    print("="*60)

    critical_packages = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("langgraph", "LangGraph"),
        ("langchain", "LangChain"),
        ("sklearn", "Scikit-learn"),
        ("xgboost", "XGBoost"),
        ("pandas", "Pandas"),
        ("numpy", "NumPy"),
        ("mlflow", "MLflow"),
        ("chromadb", "ChromaDB"),
        ("faker", "Faker"),
        ("pydantic", "Pydantic"),
    ]

    all_installed = True
    for package, name in critical_packages:
        try:
            __import__(package)
            print(f"  [OK] {name}")
        except ImportError:
            print(f"  [FAIL] {name} - not installed")
            all_installed = False

    return all_installed


def check_nodejs():
    """Check if Node.js and npm are available."""
    print("\n" + "="*60)
    print("[INFO] Checking Node.js and npm")
    print("="*60)

    node_ok = run_command(["node", "--version"], "Checking Node.js version")
    npm_ok = run_command(["npm", "--version"], "Checking npm version")

    if not node_ok or not npm_ok:
        print("\n[WARN] Node.js/npm not found. Frontend will require manual setup.")
        print("[INFO] Install Node.js from https://nodejs.org/ or use nvm")
        return False

    return True


def create_env_template():
    """Create a .env.template file with required environment variables."""
    project_root = Path(__file__).parent.parent
    env_template = project_root / ".env.template"

    template_content = """# Credit Risk Platform Environment Variables

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Claude API (for LLM features)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Redis (for LangGraph checkpointing)
REDIS_URL=redis://localhost:6379

# Database
DATABASE_URL=sqlite:///./credit_risk.db

# MLflow
MLFLOW_TRACKING_URI=./mlruns

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./chroma_db

# CML Specific (set by CML)
# CDSW_PROJECT_URL
# CDSW_ENGINE_ID
"""

    with open(env_template, "w") as f:
        f.write(template_content)

    print(f"\n[INFO] Created environment template: {env_template}")
    return True


def main():
    """Main installation function."""
    print("\n" + "="*60)
    print("Credit Risk Platform - Dependency Installation")
    print("="*60)

    success = True

    # Install Python packages
    if not install_python_packages():
        print("\n[ERROR] Failed to install Python packages")
        success = False

    # Verify Python packages
    if not verify_python_packages():
        print("\n[WARN] Some Python packages may not be installed correctly")
        success = False

    # Check Node.js (optional for backend-only development)
    check_nodejs()

    # Create .env template
    create_env_template()

    # Summary
    print("\n" + "="*60)
    print("Installation Summary")
    print("="*60)

    if success:
        print("[SUCCESS] All dependencies installed successfully!")
        print("\nNext steps:")
        print("  1. Copy .env.template to .env and fill in your API keys")
        print("  2. Run 0_setup/create_tables.py to set up the database")
        print("  3. Run 0_setup/setup_vector_store.py to initialize ChromaDB")
    else:
        print("[WARNING] Some installations failed. Check the logs above.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Configure CML Model Endpoints

Auto-discovers deployed model endpoints and configures environment variables.
Run this after AMP deployment to enable CML model serving.

Usage:
    python 0_setup/configure_endpoints.py

Or run as a CML Job after model deployment.
"""

import os
import json
from pathlib import Path

# Get project root from environment or current working directory
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))

# Check if running in CML
CDSW_PROJECT_ID = os.environ.get("CDSW_PROJECT_ID")
CDSW_DOMAIN = os.environ.get("CDSW_DOMAIN")
CDSW_API_KEY = os.environ.get("CDSW_API_KEY") or os.environ.get("CDSW_APIV2_KEY")


def get_cml_client():
    """Get CML API client if available."""
    try:
        import cmlapi
        client = cmlapi.default_client()
        return client
    except ImportError:
        print("[WARN] cmlapi not available. Install with: pip install cmlapi")
        return None
    except Exception as e:
        print(f"[WARN] Could not initialize CML client: {e}")
        return None


def discover_model_endpoints():
    """Discover deployed model endpoints in the current project."""
    client = get_cml_client()

    if not client:
        print("[INFO] CML API not available. Manual configuration required.")
        return {}

    if not CDSW_PROJECT_ID:
        print("[WARN] Not running in CML environment (CDSW_PROJECT_ID not set)")
        return {}

    print(f"[INFO] Discovering models in project {CDSW_PROJECT_ID}...")

    endpoints = {}

    try:
        # List all models in the project
        models = client.list_models(project_id=CDSW_PROJECT_ID)

        # Model entity labels we're looking for
        model_mapping = {
            "pd_model": "PD_MODEL_ENDPOINT",
            "lgd_model": "LGD_MODEL_ENDPOINT",
            "risk_engine": "RISK_ENGINE_ENDPOINT",
            "document_processor": "DOCUMENT_ENDPOINT",
            "rag_query": "RAG_ENDPOINT",
        }

        for model in models.models:
            # Check if this model matches our expected labels
            for label, env_var in model_mapping.items():
                if label in model.name.lower() or (hasattr(model, 'description') and label in (model.description or '').lower()):
                    # Get the model's access URL
                    if hasattr(model, 'access_key') and model.access_key:
                        # Construct the endpoint URL
                        endpoint_url = f"https://{model.access_key}.{CDSW_DOMAIN}/predict"
                        endpoints[env_var] = endpoint_url
                        print(f"  [OK] Found {label}: {endpoint_url}")
                    break

        # Also try to get from model builds/deployments
        for model in models.models:
            try:
                builds = client.list_model_builds(
                    project_id=CDSW_PROJECT_ID,
                    model_id=model.id
                )
                for build in builds.model_builds:
                    if build.status == "built":
                        deployments = client.list_model_deployments(
                            project_id=CDSW_PROJECT_ID,
                            model_id=model.id,
                            build_id=build.id
                        )
                        for deployment in deployments.model_deployments:
                            if deployment.status == "deployed":
                                print(f"  [INFO] Active deployment found for {model.name}")
            except Exception as e:
                pass  # Ignore errors for individual models

    except Exception as e:
        print(f"[ERROR] Failed to list models: {e}")

    return endpoints


def write_env_file(endpoints: dict, env_file: Path = None):
    """Write discovered endpoints to .env file."""
    if not env_file:
        env_file = PROJECT_ROOT / ".env"

    # Read existing .env
    existing_lines = []
    if env_file.exists():
        existing_lines = env_file.read_text().splitlines()

    # Update or add endpoint variables
    updated_vars = set()
    new_lines = []

    for line in existing_lines:
        # Check if this line sets one of our endpoint vars
        var_name = line.split('=')[0].strip() if '=' in line else None
        if var_name in endpoints:
            new_lines.append(f"{var_name}={endpoints[var_name]}")
            updated_vars.add(var_name)
        else:
            new_lines.append(line)

    # Add any new variables not already in file
    for var_name, value in endpoints.items():
        if var_name not in updated_vars:
            new_lines.append(f"{var_name}={value}")

    # Also set CML_DEPLOYMENT_MODE if we found endpoints
    if endpoints and "CML_DEPLOYMENT_MODE=cml" not in '\n'.join(new_lines):
        # Check if CML_DEPLOYMENT_MODE exists
        mode_set = False
        final_lines = []
        for line in new_lines:
            if line.startswith("CML_DEPLOYMENT_MODE="):
                final_lines.append("CML_DEPLOYMENT_MODE=cml")
                mode_set = True
            else:
                final_lines.append(line)
        if not mode_set:
            final_lines.append("CML_DEPLOYMENT_MODE=cml")
        new_lines = final_lines

    # Write back
    env_file.write_text('\n'.join(new_lines) + '\n')
    print(f"\n[OK] Updated {env_file}")


def print_manual_instructions():
    """Print instructions for manual configuration."""
    print("""
================================================================================
Manual Configuration Instructions
================================================================================

If auto-discovery didn't work, configure endpoints manually:

1. Get Model URLs from CML UI:
   - Go to your Project → Models tab
   - Click on each model to get its Access URL

2. Set Environment Variables:
   - Go to Project Settings → Advanced → Environment Variables
   - Add these variables:

     CML_DEPLOYMENT_MODE=cml
     PD_MODEL_ENDPOINT=https://<pd-model-access-key>.<domain>/predict
     LGD_MODEL_ENDPOINT=https://<lgd-model-access-key>.<domain>/predict

3. Restart the Credit Risk API application

================================================================================
""")


def main():
    print("\n" + "=" * 60)
    print("CML Model Endpoint Configuration")
    print("=" * 60 + "\n")

    # Check environment
    if CDSW_PROJECT_ID:
        print(f"[INFO] Running in CML project: {CDSW_PROJECT_ID}")
        print(f"[INFO] Domain: {CDSW_DOMAIN}")
    else:
        print("[INFO] Not running in CML environment")
        print("[INFO] Set CDSW_PROJECT_ID and CDSW_DOMAIN for auto-discovery")

    # Discover endpoints
    endpoints = discover_model_endpoints()

    if endpoints:
        print(f"\n[OK] Discovered {len(endpoints)} model endpoints")

        # Write to .env file
        write_env_file(endpoints)

        print("\n[INFO] Endpoints configured. Restart the API application to apply changes.")
        print("\nDiscovered endpoints:")
        for var, url in endpoints.items():
            print(f"  {var}={url}")
    else:
        print("\n[WARN] No endpoints discovered automatically")
        print_manual_instructions()

    return 0


if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
"""
Test MLflow Configuration

This script tests the environment-aware MLflow configuration to ensure
it works correctly in both local and production environments.

Usage:
    # Test local configuration
    python scripts/test_mlflow_config.py

    # Test production configuration
    APP_ENV=production python scripts/test_mlflow_config.py

    # Test with custom tracking URI
    MLFLOW_TRACKING_URI=http://example.com/mlflow python scripts/test_mlflow_config.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_config_loading():
    """Test that configuration loads correctly."""
    print("\n" + "=" * 70)
    print("Testing MLflow Configuration")
    print("=" * 70)

    # Test environment detection
    env = os.environ.get("APP_ENV", "local")
    print(f"\n1. Environment Detection")
    print(f"   APP_ENV: {env}")

    # Detect Cloudera ML
    cml_vars = ["CDSW_PROJECT_URL", "CML_DOMAIN", "HADOOP_CONF_DIR"]
    cml_detected = any(var in os.environ for var in cml_vars)
    print(f"   Cloudera ML Detected: {cml_detected}")
    if cml_detected:
        print(f"   Found: {[v for v in cml_vars if v in os.environ]}")

    # Load backend configuration
    print(f"\n2. Loading Backend Configuration")
    try:
        from config.config_loader import get_config, get_environment, is_production, is_local

        config_env = get_environment()
        print(f"   Config Environment: {config_env}")
        print(f"   Is Production: {is_production()}")
        print(f"   Is Local: {is_local()}")

        config = get_config()
        mlflow_config = config.get("mlflow", {})
        print(f"\n   MLflow Config from YAML:")
        print(f"   - tracking_uri: {mlflow_config.get('tracking_uri')}")
        print(f"   - experiment_name: {mlflow_config.get('experiment_name')}")
        print(f"   - registry_uri: {mlflow_config.get('registry_uri')}")

    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    # Test Settings class
    print(f"\n3. Testing Settings Class")
    try:
        # Import from 5_backend directory
        import importlib.util
        backend_config_path = Path(__file__).parent.parent / "5_backend" / "config.py"
        spec = importlib.util.spec_from_file_location("backend_config", backend_config_path)
        backend_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend_config)
        settings = backend_config.settings

        print(f"   Settings loaded successfully")
        print(f"   Environment: {settings.app_env}")
        print(f"   MLflow Tracking URI: {settings.mlflow_tracking_uri}")
        print(f"   MLflow Experiment: {settings.mlflow_experiment_name}")

    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    # Test MLflow configuration
    print(f"\n4. Testing MLflow Configuration Method")
    try:
        mlflow_info = settings.configure_mlflow()

        print(f"   Status: {mlflow_info.get('status')}")
        print(f"   Tracking URI: {mlflow_info.get('tracking_uri')}")
        print(f"   Registry URI: {mlflow_info.get('registry_uri')}")
        print(f"   Experiment: {mlflow_info.get('experiment_name')}")
        print(f"   Environment: {mlflow_info.get('environment')}")

        if mlflow_info.get("auth_method"):
            print(f"   Auth Method: {mlflow_info['auth_method']}")

        if mlflow_info["status"] != "configured":
            print(f"   WARNING: {mlflow_info.get('message')}")
            return False

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test MLflow client
    print(f"\n5. Testing MLflow Client")
    try:
        import mlflow
        from mlflow.tracking import MlflowClient

        client = MlflowClient()
        tracking_uri = mlflow.get_tracking_uri()
        print(f"   MLflow Tracking URI: {tracking_uri}")

        # Try to list experiments (read operation)
        try:
            experiments = client.search_experiments()
            print(f"   Experiments Found: {len(experiments)}")
            if experiments:
                for exp in experiments[:3]:
                    print(f"     - {exp.name} (ID: {exp.experiment_id})")
        except Exception as e:
            print(f"   WARNING: Could not list experiments: {e}")

    except ImportError:
        print(f"   WARNING: MLflow not installed")
        print(f"   Run: pip install mlflow")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_environment_variables():
    """Test environment variable override."""
    print(f"\n6. Environment Variable Override Test")

    env_vars = [
        "MLFLOW_TRACKING_URI",
        "MLFLOW_EXPERIMENT_NAME",
        "MLFLOW_REGISTRY_URI",
        "MLFLOW_TRACKING_USERNAME",
        "MLFLOW_TRACKING_PASSWORD",
        "MLFLOW_TRACKING_TOKEN",
    ]

    set_vars = {var: os.environ.get(var) for var in env_vars if os.environ.get(var)}

    if set_vars:
        print(f"   Environment Variables Set:")
        for var, value in set_vars.items():
            # Mask sensitive values
            if "PASSWORD" in var or "TOKEN" in var:
                masked = value[:4] + "*" * (len(value) - 4) if len(value) > 4 else "****"
                print(f"   - {var}: {masked}")
            else:
                print(f"   - {var}: {value}")
    else:
        print(f"   No MLflow environment variables set (using config defaults)")

    return True


def test_file_paths():
    """Test that required directories and files exist."""
    print(f"\n7. File Path Verification")

    project_root = Path(__file__).parent.parent
    paths_to_check = [
        ("Config: local.yaml", project_root / "config" / "local.yaml"),
        ("Config: production.yaml", project_root / "config" / "production.yaml"),
        ("Config Loader", project_root / "config" / "config_loader.py"),
        ("Backend Config", project_root / "5_backend" / "config.py"),
        ("Register Models", project_root / "3_models" / "register_models.py"),
    ]

    all_exist = True
    for name, path in paths_to_check:
        exists = path.exists()
        status = "✓" if exists else "✗"
        print(f"   {status} {name}: {path}")
        if not exists:
            all_exist = False

    return all_exist


def print_recommendations():
    """Print recommendations based on environment."""
    print(f"\n" + "=" * 70)
    print("Recommendations")
    print("=" * 70)

    env = os.environ.get("APP_ENV", "local")

    if env == "local":
        print("\nLocal Development Setup:")
        print("  1. Install dependencies:")
        print("     pip install mlflow python-dotenv")
        print("\n  2. Start MLflow UI:")
        print("     mlflow ui --backend-store-uri ./mlruns")
        print("     Open: http://localhost:5000")
        print("\n  3. Register models:")
        print("     python 3_models/register_models.py")

    else:
        print("\nProduction Setup (Cloudera ML):")
        print("  1. Set environment variables in Cloudera ML:")
        print("     - APP_ENV=production")
        print("     - MLFLOW_TRACKING_URI=https://your-workspace.ml.cloudera.site/mlflow")
        print("     - MLFLOW_TRACKING_USERNAME=your_username")
        print("     - MLFLOW_TRACKING_PASSWORD=your_password")
        print("\n  2. Or use GitHub Secrets for CI/CD deployment")
        print("\n  3. Verify connectivity:")
        print("     mlflow experiments list")

    print("\nFor more information, see: docs/MLFLOW_CONFIGURATION.md")


def main():
    """Main test function."""
    print("\n" + "=" * 70)
    print("MLflow Configuration Test Suite")
    print("=" * 70)

    # Load .env if it exists
    try:
        from dotenv import load_dotenv
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print(f"\nLoaded .env file: {env_file}")
    except ImportError:
        pass

    # Run tests
    results = {
        "Config Loading": test_config_loading(),
        "Environment Variables": test_environment_variables(),
        "File Paths": test_file_paths(),
    }

    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed. See details above.")

    # Print recommendations
    print_recommendations()

    print("\n" + "=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

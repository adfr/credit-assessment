#!/usr/bin/env python3
"""
MLflow Model Registry Script
Registers trained models in MLflow Model Registry.
"""

import os
import sys
import pickle
from pathlib import Path
from datetime import datetime

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False


def load_model(model_type: str) -> dict:
    """Load trained model artifact."""
    project_root = Path(__file__).parent.parent
    model_path = project_root / "data" / "models" / model_type / f"{model_type}_model_latest.pkl"

    if not model_path.exists():
        return None

    with open(model_path, "rb") as f:
        return pickle.load(f)


def setup_mlflow():
    """Setup MLflow tracking."""
    project_root = Path(__file__).parent.parent
    tracking_uri = str(project_root / "mlruns")

    mlflow.set_tracking_uri(tracking_uri)
    return MlflowClient(tracking_uri)


def register_pd_model(client: MlflowClient):
    """Register PD model in MLflow."""
    print("\n[INFO] Registering PD model...")

    model_data = load_model("pd")
    if not model_data:
        print("  [WARN] PD model not found, skipping")
        return None

    model_name = "credit_risk_pd_model"

    # Set experiment
    mlflow.set_experiment("pd_model_registry")

    with mlflow.start_run(run_name="pd_model_registration"):
        # Log model
        model = model_data["model"]
        model_type = type(model).__name__

        if "XGB" in model_type:
            mlflow.xgboost.log_model(model, "model", registered_model_name=model_name)
        else:
            mlflow.sklearn.log_model(model, "model", registered_model_name=model_name)

        # Log metrics
        for metric_name, metric_value in model_data["metrics"].items():
            mlflow.log_metric(metric_name, metric_value)

        # Log parameters
        mlflow.log_param("model_type", model_data.get("model_name", "unknown"))
        mlflow.log_param("n_features", len(model_data["features"]))
        mlflow.log_param("trained_at", model_data.get("trained_at", "unknown"))

        # Get run ID
        run_id = mlflow.active_run().info.run_id

    print(f"  - Registered as: {model_name}")
    print(f"  - Run ID: {run_id}")

    # Transition to staging
    try:
        latest_version = client.get_latest_versions(model_name, stages=["None"])[0]
        client.transition_model_version_stage(
            name=model_name,
            version=latest_version.version,
            stage="Staging"
        )
        print(f"  - Version {latest_version.version} moved to Staging")
    except Exception as e:
        print(f"  [WARN] Could not transition to Staging: {e}")

    return model_name


def register_lgd_model(client: MlflowClient):
    """Register LGD model in MLflow."""
    print("\n[INFO] Registering LGD model...")

    model_data = load_model("lgd")
    if not model_data:
        print("  [WARN] LGD model not found, skipping")
        return None

    model_name = "credit_risk_lgd_model"

    # Set experiment
    mlflow.set_experiment("lgd_model_registry")

    with mlflow.start_run(run_name="lgd_model_registration"):
        # Log model
        model = model_data["model"]
        model_type = type(model).__name__

        if "XGB" in model_type:
            mlflow.xgboost.log_model(model, "model", registered_model_name=model_name)
        else:
            mlflow.sklearn.log_model(model, "model", registered_model_name=model_name)

        # Log metrics
        for metric_name, metric_value in model_data["metrics"].items():
            mlflow.log_metric(metric_name, metric_value)

        # Log parameters
        mlflow.log_param("model_type", model_data.get("model_name", "unknown"))
        mlflow.log_param("n_features", len(model_data["features"]))
        mlflow.log_param("trained_at", model_data.get("trained_at", "unknown"))

        run_id = mlflow.active_run().info.run_id

    print(f"  - Registered as: {model_name}")
    print(f"  - Run ID: {run_id}")

    # Transition to staging
    try:
        latest_version = client.get_latest_versions(model_name, stages=["None"])[0]
        client.transition_model_version_stage(
            name=model_name,
            version=latest_version.version,
            stage="Staging"
        )
        print(f"  - Version {latest_version.version} moved to Staging")
    except Exception as e:
        print(f"  [WARN] Could not transition to Staging: {e}")

    return model_name


def list_registered_models(client: MlflowClient):
    """List all registered models."""
    print("\n" + "=" * 60)
    print("Registered Models")
    print("=" * 60)

    try:
        models = client.search_registered_models()
        if not models:
            print("  No models registered yet")
            return

        for model in models:
            print(f"\n  Model: {model.name}")
            versions = client.get_latest_versions(model.name)
            for v in versions:
                print(f"    - Version {v.version}: {v.current_stage}")
    except Exception as e:
        print(f"  [ERROR] Could not list models: {e}")


def promote_to_production(client: MlflowClient, model_name: str, version: int = None):
    """Promote a model version to Production."""
    print(f"\n[INFO] Promoting {model_name} to Production...")

    try:
        if version is None:
            # Get latest staging version
            versions = client.get_latest_versions(model_name, stages=["Staging"])
            if not versions:
                print("  [WARN] No staging version found")
                return
            version = versions[0].version

        # Archive current production version
        prod_versions = client.get_latest_versions(model_name, stages=["Production"])
        for pv in prod_versions:
            client.transition_model_version_stage(
                name=model_name,
                version=pv.version,
                stage="Archived"
            )
            print(f"  - Archived previous production version {pv.version}")

        # Promote to production
        client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage="Production"
        )
        print(f"  - Version {version} promoted to Production")

    except Exception as e:
        print(f"  [ERROR] Promotion failed: {e}")


def main():
    """Main function to register models."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - Model Registration")
    print("=" * 60)

    if not MLFLOW_AVAILABLE:
        print("\n[ERROR] MLflow not installed. Run: pip install mlflow")
        print("Models will be saved locally but not registered in MLflow")

        # Show local model info instead
        for model_type in ["pd", "lgd"]:
            model_data = load_model(model_type)
            if model_data:
                print(f"\n{model_type.upper()} Model:")
                print(f"  - Type: {model_data.get('model_name', 'unknown')}")
                print(f"  - Features: {len(model_data.get('features', []))}")
                print(f"  - Trained: {model_data.get('trained_at', 'unknown')}")
                print(f"  - Metrics: {model_data.get('metrics', {})}")

        return 0

    # Setup MLflow
    client = setup_mlflow()

    # Register models
    pd_model_name = register_pd_model(client)
    lgd_model_name = register_lgd_model(client)

    # List registered models
    list_registered_models(client)

    # Optionally promote to production
    print("\n" + "=" * 60)
    print("Model Registration Summary")
    print("=" * 60)

    if pd_model_name:
        print(f"\n  PD Model: {pd_model_name} (Staging)")
    if lgd_model_name:
        print(f"  LGD Model: {lgd_model_name} (Staging)")

    print("\n  To promote to Production, run:")
    print("    python register_models.py --promote pd")
    print("    python register_models.py --promote lgd")

    # Handle command line args for promotion
    if len(sys.argv) > 2 and sys.argv[1] == "--promote":
        model_type = sys.argv[2].lower()
        if model_type == "pd" and pd_model_name:
            promote_to_production(client, pd_model_name)
        elif model_type == "lgd" and lgd_model_name:
            promote_to_production(client, lgd_model_name)
        else:
            print(f"  [ERROR] Unknown model type: {model_type}")

    print("\n" + "=" * 60)
    print("[SUCCESS] Model registration completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Deploy models using 4_endpoints/serve_pd.py")
    print("  2. Start backend with 5_backend/main.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())

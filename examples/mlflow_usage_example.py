#!/usr/bin/env python3
"""
MLflow Usage Example

Demonstrates how to use environment-aware MLflow configuration
in the Credit Risk Platform.

This example works in both local and production environments.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def example_basic_usage():
    """Example: Basic MLflow configuration and usage."""
    print("\n" + "=" * 70)
    print("Example 1: Basic MLflow Configuration")
    print("=" * 70)

    # Import backend configuration
    import importlib.util
    backend_config_path = Path(__file__).parent.parent / "5_backend" / "config.py"
    spec = importlib.util.spec_from_file_location("backend_config", backend_config_path)
    backend_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend_config)
    settings = backend_config.settings

    # Configure MLflow - this is all you need!
    mlflow_info = settings.configure_mlflow()

    print("\nMLflow Configuration:")
    print(f"  Status: {mlflow_info['status']}")
    print(f"  Tracking URI: {mlflow_info.get('tracking_uri')}")
    print(f"  Experiment: {mlflow_info.get('experiment_name')}")
    print(f"  Environment: {mlflow_info.get('environment')}")

    if mlflow_info["status"] != "configured":
        print(f"\n{mlflow_info.get('message')}")
        return

    # Now MLflow is ready to use
    try:
        import mlflow
        print("\nMLflow is ready to use!")
        print(f"Tracking URI: {mlflow.get_tracking_uri()}")
    except ImportError:
        print("\nMLflow is not installed. Install with: pip install mlflow")


def example_model_training():
    """Example: Training a model with MLflow tracking."""
    print("\n" + "=" * 70)
    print("Example 2: Model Training with MLflow")
    print("=" * 70)

    try:
        import mlflow
        import mlflow.sklearn
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.datasets import make_classification
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, roc_auc_score
    except ImportError as e:
        print(f"\nRequired libraries not installed: {e}")
        print("Install with: pip install mlflow scikit-learn")
        return

    # Configure MLflow
    import importlib.util
    backend_config_path = Path(__file__).parent.parent / "5_backend" / "config.py"
    spec = importlib.util.spec_from_file_location("backend_config", backend_config_path)
    backend_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend_config)
    settings = backend_config.settings

    mlflow_info = settings.configure_mlflow()
    if mlflow_info["status"] != "configured":
        print(f"\n{mlflow_info.get('message')}")
        return

    print("\nTraining example model...")

    # Generate sample data
    X, y = make_classification(n_samples=1000, n_features=20, n_informative=15, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Start MLflow run
    with mlflow.start_run(run_name="example_rf_model"):
        # Train model
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X_train, y_train)

        # Predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_pred_proba)

        # Log parameters
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("max_depth", 5)
        mlflow.log_param("n_features", X_train.shape[1])

        # Log metrics
        mlflow.log_metric("accuracy", accuracy)
        mlflow.log_metric("auc", auc)

        # Log model
        mlflow.sklearn.log_model(model, "model")

        print(f"\nModel trained successfully!")
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  AUC: {auc:.4f}")
        print(f"  Run ID: {mlflow.active_run().info.run_id}")


def example_model_loading():
    """Example: Loading a model from MLflow."""
    print("\n" + "=" * 70)
    print("Example 3: Loading Model from MLflow")
    print("=" * 70)

    try:
        import mlflow
        import mlflow.sklearn
    except ImportError:
        print("\nMLflow not installed. Install with: pip install mlflow")
        return

    # Configure MLflow
    import importlib.util
    backend_config_path = Path(__file__).parent.parent / "5_backend" / "config.py"
    spec = importlib.util.spec_from_file_location("backend_config", backend_config_path)
    backend_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend_config)
    settings = backend_config.settings

    mlflow_info = settings.configure_mlflow()
    if mlflow_info["status"] != "configured":
        print(f"\n{mlflow_info.get('message')}")
        return

    # List recent runs
    from mlflow.tracking import MlflowClient
    client = MlflowClient()

    try:
        experiments = client.search_experiments()
        if not experiments:
            print("\nNo experiments found. Run example 2 first to create a model.")
            return

        print(f"\nFound {len(experiments)} experiment(s):")
        for exp in experiments[:3]:
            print(f"  - {exp.name} (ID: {exp.experiment_id})")

            # Get recent runs
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=3,
                order_by=["start_time DESC"]
            )

            if runs:
                print(f"    Recent runs:")
                for run in runs:
                    metrics = run.data.metrics
                    print(f"      - {run.info.run_name} (ID: {run.info.run_id})")
                    if "accuracy" in metrics:
                        print(f"        Accuracy: {metrics['accuracy']:.4f}")

    except Exception as e:
        print(f"\nError listing experiments: {e}")


def example_production_usage():
    """Example: Production-specific usage with Cloudera MLflow."""
    print("\n" + "=" * 70)
    print("Example 4: Production Usage (Cloudera ML)")
    print("=" * 70)

    # Configure MLflow
    import importlib.util
    backend_config_path = Path(__file__).parent.parent / "5_backend" / "config.py"
    spec = importlib.util.spec_from_file_location("backend_config", backend_config_path)
    backend_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend_config)
    settings = backend_config.settings
    is_production = backend_config.is_production

    if not is_production():
        print("\nNot running in production environment.")
        print("To test production configuration, run:")
        print("  APP_ENV=production python examples/mlflow_usage_example.py")
        return

    print("\nProduction environment detected!")
    print(f"  Tracking URI: {settings.mlflow_tracking_uri}")

    if settings.mlflow_tracking_uri.startswith("http"):
        print("  Using remote Cloudera MLflow server")
        if settings.mlflow_tracking_username:
            print(f"  Authentication: Basic (username: {settings.mlflow_tracking_username})")
        elif settings.mlflow_tracking_token:
            print("  Authentication: Token")
    else:
        print("  Using CML filesystem for MLflow")

    # Configure and test connection
    mlflow_info = settings.configure_mlflow()
    print(f"\nConfiguration Status: {mlflow_info['status']}")

    if mlflow_info["status"] == "configured":
        print("MLflow is ready for production use!")
    else:
        print(f"Configuration issue: {mlflow_info.get('message')}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MLflow Configuration Examples")
    print("=" * 70)

    # Check environment
    import os
    env = os.environ.get("APP_ENV", "local")
    print(f"\nCurrent Environment: {env.upper()}")

    # Run examples
    example_basic_usage()
    example_model_training()
    example_model_loading()
    example_production_usage()

    print("\n" + "=" * 70)
    print("Examples Complete")
    print("=" * 70)
    print("\nFor more information:")
    print("  - Configuration Guide: docs/MLFLOW_CONFIGURATION.md")
    print("  - Test Configuration: python scripts/test_mlflow_config.py")
    print("  - Register Models: python 3_models/register_models.py")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()

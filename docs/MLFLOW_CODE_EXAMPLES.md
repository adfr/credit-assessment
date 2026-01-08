# MLflow Configuration - Code Examples

This document provides code examples for using the environment-aware MLflow configuration.

## Table of Contents

1. [Basic Configuration](#basic-configuration)
2. [Backend Integration](#backend-integration)
3. [Model Training](#model-training)
4. [Model Registration](#model-registration)
5. [Model Loading](#model-loading)
6. [Custom Experiments](#custom-experiments)
7. [Error Handling](#error-handling)
8. [Testing Configuration](#testing-configuration)

---

## Basic Configuration

### Import and Configure MLflow

```python
from config import settings
import mlflow

# Configure MLflow (call once at application startup)
mlflow_info = settings.configure_mlflow()

# Check configuration status
if mlflow_info["status"] == "configured":
    print(f"MLflow configured successfully")
    print(f"Tracking URI: {mlflow_info['tracking_uri']}")
    print(f"Environment: {mlflow_info['environment']}")
else:
    print(f"MLflow configuration failed: {mlflow_info['message']}")
```

### Environment Detection

```python
from config import settings, is_production, is_local

# Check environment
if is_production():
    print("Running in production")
    print(f"MLflow URI: {settings.mlflow_tracking_uri}")
    # Use production-specific settings
else:
    print("Running locally")
    print(f"MLflow URI: {settings.mlflow_tracking_uri}")
    # Use local-specific settings
```

---

## Backend Integration

### FastAPI Application

```python
from fastapi import FastAPI, HTTPException
from config import settings, is_production
import mlflow

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Configure MLflow on application startup."""
    mlflow_info = settings.configure_mlflow()

    if mlflow_info["status"] != "configured":
        raise RuntimeError(f"MLflow configuration failed: {mlflow_info['message']}")

    print(f"MLflow configured:")
    print(f"  - Tracking URI: {mlflow_info['tracking_uri']}")
    print(f"  - Environment: {mlflow_info['environment']}")
    if mlflow_info.get("auth_method"):
        print(f"  - Authentication: {mlflow_info['auth_method']}")

@app.get("/health/mlflow")
async def mlflow_health():
    """Check MLflow connectivity."""
    try:
        from mlflow.tracking import MlflowClient
        client = MlflowClient()
        experiments = client.search_experiments(max_results=1)
        return {
            "status": "healthy",
            "tracking_uri": settings.mlflow_tracking_uri,
            "experiments_count": len(experiments),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MLflow unhealthy: {str(e)}")

@app.get("/config/mlflow")
async def get_mlflow_config():
    """Get MLflow configuration info."""
    return {
        "environment": settings.app_env,
        "tracking_uri": settings.mlflow_tracking_uri,
        "experiment_name": settings.mlflow_experiment_name,
        "is_production": is_production(),
    }
```

---

## Model Training

### Basic Training with MLflow

```python
from config import settings
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score

# Configure MLflow
settings.configure_mlflow()

# Your data loading code
X_train, X_test, y_train, y_test = load_and_split_data()

# Start MLflow run
with mlflow.start_run(run_name="pd_model_training"):
    # Log parameters
    mlflow.log_param("model_type", "random_forest")
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 10)
    mlflow.log_param("n_features", X_train.shape[1])

    # Train model
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)

    # Predictions and evaluation
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_proba)

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("auc", auc)
    mlflow.log_metric("n_samples_train", len(X_train))
    mlflow.log_metric("n_samples_test", len(X_test))

    # Log model
    mlflow.sklearn.log_model(
        model,
        "model",
        registered_model_name="pd_model"
    )

    # Log artifacts (optional)
    # mlflow.log_artifact("feature_importance.png")

    print(f"Model trained and logged successfully!")
    print(f"Run ID: {mlflow.active_run().info.run_id}")
    print(f"Accuracy: {accuracy:.4f}, AUC: {auc:.4f}")
```

### Training with Auto-logging

```python
from config import settings
import mlflow
import mlflow.sklearn

# Configure MLflow
settings.configure_mlflow()

# Enable auto-logging
mlflow.sklearn.autolog()

# Start run
with mlflow.start_run(run_name="auto_logged_model"):
    # Train model - parameters and metrics logged automatically
    model = RandomForestClassifier(n_estimators=100, max_depth=10)
    model.fit(X_train, y_train)

    # Make predictions - metrics logged automatically
    score = model.score(X_test, y_test)

    print(f"Model trained with auto-logging!")
    print(f"Score: {score:.4f}")
```

---

## Model Registration

### Register Model in MLflow Registry

```python
from config import settings
import mlflow
from mlflow.tracking import MlflowClient

# Configure MLflow
settings.configure_mlflow()
client = MlflowClient()

# Register existing run as a model
def register_model(run_id: str, model_name: str):
    """Register a model from an existing run."""
    model_uri = f"runs:/{run_id}/model"

    # Create or get registered model
    try:
        client.create_registered_model(model_name)
        print(f"Created new registered model: {model_name}")
    except Exception:
        print(f"Model {model_name} already exists")

    # Register this run as a new version
    model_version = mlflow.register_model(model_uri, model_name)

    print(f"Registered model version: {model_version.version}")
    return model_version

# Usage
run_id = "your_run_id_here"
model_version = register_model(run_id, "pd_model")
```

### Transition Model Stage

```python
from mlflow.tracking import MlflowClient
from config import settings

settings.configure_mlflow()
client = MlflowClient()

def promote_model(model_name: str, version: int, stage: str = "Production"):
    """Promote a model version to a stage (Staging, Production, Archived)."""
    # Archive existing production version
    if stage == "Production":
        prod_versions = client.get_latest_versions(model_name, stages=["Production"])
        for pv in prod_versions:
            client.transition_model_version_stage(
                name=model_name,
                version=pv.version,
                stage="Archived"
            )
            print(f"Archived previous production version {pv.version}")

    # Promote new version
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage
    )
    print(f"Promoted {model_name} version {version} to {stage}")

# Usage
promote_model("pd_model", version=3, stage="Production")
```

---

## Model Loading

### Load Model from Registry

```python
from config import settings
import mlflow
import mlflow.sklearn

settings.configure_mlflow()

# Load latest version by stage
def load_production_model(model_name: str):
    """Load the production version of a model."""
    model_uri = f"models:/{model_name}/Production"
    model = mlflow.sklearn.load_model(model_uri)
    return model

# Load specific version
def load_model_version(model_name: str, version: int):
    """Load a specific version of a model."""
    model_uri = f"models:/{model_name}/{version}"
    model = mlflow.sklearn.load_model(model_uri)
    return model

# Usage
model = load_production_model("pd_model")
predictions = model.predict(X_test)
```

### Load Model with Metadata

```python
from config import settings
from mlflow.tracking import MlflowClient
import mlflow.sklearn

settings.configure_mlflow()
client = MlflowClient()

def load_model_with_info(model_name: str, stage: str = "Production"):
    """Load model with metadata."""
    # Get model version info
    versions = client.get_latest_versions(model_name, stages=[stage])
    if not versions:
        raise ValueError(f"No {stage} version found for {model_name}")

    version = versions[0]
    print(f"Loading {model_name} version {version.version} ({stage})")

    # Get run information
    run = client.get_run(version.run_id)
    print(f"Trained at: {run.data.tags.get('mlflow.runName', 'unknown')}")
    print(f"Metrics: {run.data.metrics}")

    # Load model
    model_uri = f"models:/{model_name}/{stage}"
    model = mlflow.sklearn.load_model(model_uri)

    return model, version, run

# Usage
model, version, run = load_model_with_info("pd_model")
```

---

## Custom Experiments

### Set Custom Experiment

```python
from config import settings
import mlflow

settings.configure_mlflow()

# Set or create experiment
experiment_name = "pd_model_hyperparameter_tuning"
mlflow.set_experiment(experiment_name)

# Now all runs go to this experiment
with mlflow.start_run(run_name="grid_search_run_1"):
    # Your training code
    pass
```

### Nested Runs (Parent/Child)

```python
from config import settings
import mlflow

settings.configure_mlflow()

# Parent run for hyperparameter search
with mlflow.start_run(run_name="hyperparameter_search") as parent_run:
    mlflow.log_param("search_strategy", "grid_search")

    # Child runs for each parameter combination
    for n_est in [50, 100, 200]:
        for max_depth in [5, 10, 15]:
            with mlflow.start_run(
                run_name=f"n_est_{n_est}_depth_{max_depth}",
                nested=True
            ):
                mlflow.log_param("n_estimators", n_est)
                mlflow.log_param("max_depth", max_depth)

                # Train and evaluate
                model = RandomForestClassifier(
                    n_estimators=n_est,
                    max_depth=max_depth
                )
                model.fit(X_train, y_train)
                score = model.score(X_test, y_test)

                mlflow.log_metric("accuracy", score)
                print(f"n_est={n_est}, depth={max_depth}, score={score:.4f}")

    print(f"Hyperparameter search complete!")
    print(f"Parent run ID: {parent_run.info.run_id}")
```

---

## Error Handling

### Graceful MLflow Configuration

```python
from config import settings
import mlflow
from typing import Optional

def configure_mlflow_safe() -> dict:
    """
    Safely configure MLflow with error handling.

    Returns configuration info dict with status.
    """
    try:
        mlflow_info = settings.configure_mlflow()

        if mlflow_info["status"] != "configured":
            print(f"Warning: {mlflow_info.get('message')}")
            return {"status": "warning", "message": mlflow_info.get("message")}

        return mlflow_info

    except Exception as e:
        print(f"Error configuring MLflow: {e}")
        return {"status": "error", "message": str(e)}

# Usage
mlflow_info = configure_mlflow_safe()

if mlflow_info["status"] == "configured":
    # MLflow is ready
    with mlflow.start_run():
        pass
else:
    # Fallback: save model locally without MLflow
    print("Falling back to local model storage")
    # Your fallback code
```

### Safe Model Logging

```python
import mlflow
from config import settings

settings.configure_mlflow()

def log_model_safe(model, model_name: str, run_name: str = None):
    """Log model with error handling."""
    try:
        with mlflow.start_run(run_name=run_name):
            # Try to log model
            mlflow.sklearn.log_model(
                model,
                "model",
                registered_model_name=model_name
            )
            print(f"Model {model_name} logged successfully")
            return True

    except Exception as e:
        print(f"Error logging model: {e}")

        # Fallback: save locally
        import pickle
        fallback_path = f"./models/{model_name}_fallback.pkl"
        with open(fallback_path, "wb") as f:
            pickle.dump(model, f)
        print(f"Model saved to fallback location: {fallback_path}")
        return False

# Usage
success = log_model_safe(model, "pd_model", run_name="pd_v1")
```

---

## Testing Configuration

### Verify MLflow Connection

```python
from config import settings
from mlflow.tracking import MlflowClient

def test_mlflow_connection() -> bool:
    """Test MLflow connectivity and configuration."""
    try:
        # Configure MLflow
        mlflow_info = settings.configure_mlflow()

        if mlflow_info["status"] != "configured":
            print(f"Configuration failed: {mlflow_info['message']}")
            return False

        # Test connection
        client = MlflowClient()
        experiments = client.search_experiments(max_results=1)

        print(f"MLflow connection successful!")
        print(f"Tracking URI: {mlflow_info['tracking_uri']}")
        print(f"Experiments found: {len(experiments)}")

        return True

    except Exception as e:
        print(f"MLflow connection test failed: {e}")
        return False

# Usage
if test_mlflow_connection():
    print("MLflow is ready to use")
else:
    print("MLflow is not available - check configuration")
```

### List Recent Runs

```python
from config import settings
from mlflow.tracking import MlflowClient
import mlflow

settings.configure_mlflow()
client = MlflowClient()

def list_recent_runs(experiment_name: str, limit: int = 5):
    """List recent runs for an experiment."""
    try:
        # Get experiment
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if not experiment:
            print(f"Experiment '{experiment_name}' not found")
            return []

        # Search runs
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            max_results=limit,
            order_by=["start_time DESC"]
        )

        print(f"Recent runs for '{experiment_name}':")
        for run in runs:
            metrics = run.data.metrics
            params = run.data.params
            print(f"  - {run.info.run_name} (ID: {run.info.run_id})")
            print(f"    Metrics: {metrics}")
            print(f"    Params: {params}")

        return runs

    except Exception as e:
        print(f"Error listing runs: {e}")
        return []

# Usage
runs = list_recent_runs("credit_risk_local", limit=5)
```

---

## Complete Example: End-to-End Workflow

```python
"""
Complete example: Train, evaluate, register, and deploy model with MLflow.
"""

from config import settings, is_production
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
import pickle
from pathlib import Path

def train_and_register_model(X_train, X_test, y_train, y_test):
    """Complete workflow: train, evaluate, register model."""

    # Step 1: Configure MLflow
    mlflow_info = settings.configure_mlflow()
    if mlflow_info["status"] != "configured":
        raise RuntimeError(f"MLflow not available: {mlflow_info['message']}")

    print(f"MLflow configured:")
    print(f"  Environment: {mlflow_info['environment']}")
    print(f"  Tracking URI: {mlflow_info['tracking_uri']}")

    # Step 2: Set experiment
    experiment_name = settings.mlflow_experiment_name or "credit_risk"
    mlflow.set_experiment(experiment_name)

    # Step 3: Train model with MLflow tracking
    with mlflow.start_run(run_name="pd_model_v1") as run:
        # Parameters
        params = {
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 5,
            "random_state": 42
        }

        for param, value in params.items():
            mlflow.log_param(param, value)

        # Train
        print("Training model...")
        model = RandomForestClassifier(**params)
        model.fit(X_train, y_train)

        # Evaluate
        print("Evaluating model...")
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "auc": roc_auc_score(y_test, y_pred_proba),
            "n_features": X_train.shape[1],
            "n_samples_train": len(X_train),
            "n_samples_test": len(X_test)
        }

        for metric, value in metrics.items():
            mlflow.log_metric(metric, value)

        print(f"Model performance:")
        print(f"  Accuracy: {metrics['accuracy']:.4f}")
        print(f"  AUC: {metrics['auc']:.4f}")

        # Log model
        print("Logging model to MLflow...")
        mlflow.sklearn.log_model(
            model,
            "model",
            registered_model_name="pd_model"
        )

        # Also save locally as backup
        local_path = Path("./data/models/pd/pd_model_latest.pkl")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            pickle.dump({
                "model": model,
                "metrics": metrics,
                "params": params,
                "features": list(range(X_train.shape[1]))
            }, f)

        print(f"Model saved locally: {local_path}")
        print(f"MLflow run ID: {run.info.run_id}")

    # Step 4: Promote to staging (production only)
    if is_production():
        print("Promoting model to Staging...")
        client = MlflowClient()
        versions = client.get_latest_versions("pd_model", stages=["None"])
        if versions:
            client.transition_model_version_stage(
                name="pd_model",
                version=versions[0].version,
                stage="Staging"
            )
            print(f"Model version {versions[0].version} promoted to Staging")

    print("Model training and registration complete!")
    return run.info.run_id

# Usage
# run_id = train_and_register_model(X_train, X_test, y_train, y_test)
```

---

## Summary

These code examples demonstrate:

1. **Configuration**: How to set up MLflow with environment awareness
2. **Training**: How to log metrics, parameters, and models
3. **Registration**: How to register models in the registry
4. **Loading**: How to load models for inference
5. **Error Handling**: How to handle failures gracefully
6. **Testing**: How to verify configuration and connectivity

All examples work seamlessly in both local and production environments due to the environment-aware configuration system.

For more information:
- **Quick Start**: `docs/MLFLOW_QUICKSTART.md`
- **Configuration Guide**: `docs/MLFLOW_CONFIGURATION.md`
- **Test Script**: `python scripts/test_mlflow_config.py`
- **Live Examples**: `python examples/mlflow_usage_example.py`

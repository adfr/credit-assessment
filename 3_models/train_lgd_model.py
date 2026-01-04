#!/usr/bin/env python3
"""
LGD (Loss Given Default) Model Training Script
Trains regression model to predict loss severity for defaulted loans.
"""

import os
import sys
import pickle
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore")

try:
    import pandas as pd
    import numpy as np
    import yaml
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import (
        mean_absolute_error, mean_squared_error, r2_score
    )
    import xgboost as xgb
except ImportError as e:
    print(f"[ERROR] Missing required package: {e}")
    print("Run: pip install pandas numpy scikit-learn xgboost pyyaml")
    sys.exit(1)

try:
    import mlflow
    import mlflow.sklearn
    import mlflow.xgboost
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    print("[WARN] MLflow not available. Metrics will not be tracked.")


def load_config() -> dict:
    """Load LGD model configuration."""
    config_path = Path(__file__).parent / "configs" / "lgd_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_features(config: dict) -> pd.DataFrame:
    """Load feature matrix and filter to defaulted loans."""
    project_root = Path(__file__).parent.parent
    data_path = project_root / "data" / "features" / "feature_matrix.parquet"

    if not data_path.exists():
        print(f"\n[ERROR] Feature matrix not found at {data_path}")
        print("Please run 2_features/feature_pipeline.py first")
        sys.exit(1)

    df = pd.read_parquet(data_path)
    print(f"\n[INFO] Loaded {len(df)} total observations")

    # Filter to defaulted loans only
    if config["training"]["filter_defaults_only"]:
        df = df[df["default_flag"] == 1].copy()
        print(f"  - Filtered to {len(df)} defaulted loans")

    # Check if LGD target exists
    if "lgd" not in df.columns or df["lgd"].isna().all():
        print("[ERROR] LGD target not available")
        sys.exit(1)

    # Remove rows with missing LGD
    df = df[df["lgd"].notna()]
    print(f"  - {len(df)} loans with valid LGD values")

    return df


def prepare_data(df: pd.DataFrame, config: dict) -> tuple:
    """Prepare data for training."""
    print("\n[INFO] Preparing data...")

    # Get feature list from config
    feature_list = config["features"]

    # Filter to available numeric features (exclude collateral_type for now)
    numeric_features = [f for f in feature_list if f in df.columns and f != "collateral_type"]

    # Handle collateral type encoding
    if "collateral_type" in df.columns:
        collateral_dummies = pd.get_dummies(df["collateral_type"], prefix="collateral")
        df = pd.concat([df, collateral_dummies], axis=1)
        numeric_features.extend(collateral_dummies.columns.tolist())

    missing_features = [f for f in feature_list if f not in df.columns and f != "collateral_type"]
    if missing_features:
        print(f"  [WARN] Missing features: {missing_features}")

    print(f"  - Using {len(numeric_features)} features")

    # Create feature matrix
    X = df[numeric_features].copy()
    y = df["lgd"].copy()

    # Handle missing values
    X = X.fillna(X.median())

    # Split data
    train_config = config["training"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=train_config["test_size"],
        random_state=train_config["random_state"]
    )

    print(f"  - Train set: {len(X_train)} (mean LGD: {y_train.mean():.2%})")
    print(f"  - Test set: {len(X_test)} (mean LGD: {y_test.mean():.2%})")

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    return X_train, X_test, X_train_scaled, X_test_scaled, y_train, y_test, scaler, numeric_features


def evaluate_model(y_true: np.ndarray, y_pred: np.ndarray, model_name: str) -> dict:
    """Evaluate regression model performance."""
    # Clip predictions to [0, 1]
    y_pred = np.clip(y_pred, 0, 1)

    metrics = {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
        "mse": mean_squared_error(y_true, y_pred),
        "r2": r2_score(y_true, y_pred),
        "mape": np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 0.01))) * 100
    }

    print(f"\n  {model_name} Metrics:")
    print(f"    MAE: {metrics['mae']:.4f}")
    print(f"    RMSE: {metrics['rmse']:.4f}")
    print(f"    R²: {metrics['r2']:.4f}")
    print(f"    MAPE: {metrics['mape']:.2f}%")

    return metrics


def train_gradient_boosting(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: pd.Series,
    y_test: pd.Series,
    config: dict
) -> tuple:
    """Train Gradient Boosting Regressor."""
    print("\n[INFO] Training Gradient Boosting Regressor...")

    params = config["hyperparameters"]["gradient_boosting"]

    model = GradientBoostingRegressor(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        min_samples_split=params["min_samples_split"],
        min_samples_leaf=params["min_samples_leaf"],
        subsample=params["subsample"],
        loss=params["loss"],
        random_state=config["training"]["random_state"]
    )

    model.fit(X_train, y_train)

    # Predictions
    y_pred = model.predict(X_test)

    # Evaluate
    metrics = evaluate_model(y_test, y_pred, "Gradient Boosting")

    return model, metrics, y_pred


def train_xgboost(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    config: dict,
    feature_names: list
) -> tuple:
    """Train XGBoost Regressor."""
    print("\n[INFO] Training XGBoost Regressor...")

    params = config["hyperparameters"]["xgboost"]

    model = xgb.XGBRegressor(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        min_child_weight=params["min_child_weight"],
        subsample=params["subsample"],
        colsample_bytree=params["colsample_bytree"],
        reg_alpha=params["reg_alpha"],
        reg_lambda=params["reg_lambda"],
        objective=params["objective"],
        random_state=config["training"]["random_state"]
    )

    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # Predictions
    y_pred = model.predict(X_test)

    # Evaluate
    metrics = evaluate_model(y_test, y_pred, "XGBoost")

    # Feature importance
    importance = pd.DataFrame({
        "feature": feature_names,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)

    print("\n  Top 10 Features:")
    for _, row in importance.head(10).iterrows():
        bar = "█" * int(row["importance"] * 50)
        print(f"    {row['feature']:<30} {bar} {row['importance']:.4f}")

    return model, metrics, y_pred, importance


def train_random_forest(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: pd.Series,
    y_test: pd.Series,
    config: dict
) -> tuple:
    """Train Random Forest Regressor."""
    print("\n[INFO] Training Random Forest Regressor...")

    params = config["hyperparameters"]["random_forest"]

    model = RandomForestRegressor(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        min_samples_split=params["min_samples_split"],
        min_samples_leaf=params["min_samples_leaf"],
        random_state=config["training"]["random_state"],
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    # Predictions
    y_pred = model.predict(X_test)

    # Evaluate
    metrics = evaluate_model(y_test, y_pred, "Random Forest")

    return model, metrics, y_pred


def compare_with_assumptions(y_true: pd.Series, y_pred: np.ndarray, config: dict):
    """Compare model predictions with fixed LGD assumptions."""
    print("\n[INFO] Comparison with Fixed LGD Assumptions:")

    assumptions = config["lgd_assumptions"]
    mean_assumption = np.mean(list(assumptions.values()))

    # Using mean assumption for all
    assumption_mae = mean_absolute_error(y_true, [mean_assumption] * len(y_true))
    model_mae = mean_absolute_error(y_true, y_pred)

    improvement = (assumption_mae - model_mae) / assumption_mae * 100

    print(f"  - Mean Fixed Assumption: {mean_assumption:.2%}")
    print(f"  - Fixed Assumption MAE: {assumption_mae:.4f}")
    print(f"  - Model MAE: {model_mae:.4f}")
    print(f"  - Improvement: {improvement:.1f}%")


def select_best_model(results: dict) -> str:
    """Select the best model based on MAE (lower is better)."""
    best_model = min(results.keys(), key=lambda k: results[k]["metrics"]["mae"])
    best_mae = results[best_model]["metrics"]["mae"]
    print(f"\n[INFO] Best model: {best_model} (MAE: {best_mae:.4f})")
    return best_model


def save_model(
    model,
    scaler,
    features: list,
    metrics: dict,
    model_name: str,
    config: dict
):
    """Save the trained model."""
    print(f"\n[INFO] Saving {model_name} model...")

    project_root = Path(__file__).parent.parent
    model_dir = project_root / "data" / "models" / "lgd"
    model_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = model_dir / f"lgd_model_{model_name.lower().replace(' ', '_')}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump({
            "model": model,
            "scaler": scaler,
            "features": features,
            "metrics": metrics,
            "config": config,
            "model_name": model_name,
            "trained_at": datetime.now().isoformat()
        }, f)

    print(f"  - Saved to {model_path}")

    # Save as latest
    latest_path = model_dir / "lgd_model_latest.pkl"
    with open(latest_path, "wb") as f:
        pickle.dump({
            "model": model,
            "scaler": scaler,
            "features": features,
            "metrics": metrics,
            "config": config,
            "model_name": model_name,
            "trained_at": datetime.now().isoformat()
        }, f)

    print(f"  - Saved as latest: {latest_path}")

    return model_path


def log_to_mlflow(
    model,
    metrics: dict,
    model_name: str,
    config: dict,
    feature_importance: pd.DataFrame = None
):
    """Log model to MLflow."""
    if not MLFLOW_AVAILABLE:
        return

    print(f"\n[INFO] Logging to MLflow...")

    mlflow_config = config.get("mlflow", {})
    tracking_uri = mlflow_config.get("tracking_uri", "./mlruns")
    experiment_name = mlflow_config.get("experiment_name", "lgd_model_training")

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=f"lgd_{model_name.lower().replace(' ', '_')}"):
        # Log parameters
        mlflow.log_param("model_type", model_name)
        mlflow.log_param("n_features", len(config["features"]))

        # Log metrics
        for metric_name, metric_value in metrics.items():
            mlflow.log_metric(metric_name, metric_value)

        # Log model
        if "XGBoost" in model_name:
            mlflow.xgboost.log_model(model, "model")
        else:
            mlflow.sklearn.log_model(model, "model")

        print(f"  - Logged run to {tracking_uri}")


def main():
    """Main function to train LGD model."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - LGD Model Training")
    print("=" * 60)

    # Load config
    config = load_config()
    print(f"\n[INFO] Model: {config['model']['name']} v{config['model']['version']}")

    # Load data
    df = load_features(config)

    # Prepare data
    X_train, X_test, X_train_scaled, X_test_scaled, y_train, y_test, scaler, features = prepare_data(df, config)

    # Train models
    results = {}

    # Gradient Boosting
    gb_model, gb_metrics, gb_pred = train_gradient_boosting(
        X_train, X_test, y_train, y_test, config
    )
    results["Gradient Boosting"] = {
        "model": gb_model,
        "metrics": gb_metrics,
        "predictions": gb_pred,
        "use_scaler": False
    }

    # XGBoost
    xgb_model, xgb_metrics, xgb_pred, importance = train_xgboost(
        X_train, X_test, y_train, y_test, config, features
    )
    results["XGBoost"] = {
        "model": xgb_model,
        "metrics": xgb_metrics,
        "predictions": xgb_pred,
        "importance": importance,
        "use_scaler": False
    }

    # Random Forest
    rf_model, rf_metrics, rf_pred = train_random_forest(
        X_train, X_test, y_train, y_test, config
    )
    results["Random Forest"] = {
        "model": rf_model,
        "metrics": rf_metrics,
        "predictions": rf_pred,
        "use_scaler": False
    }

    # Compare with fixed assumptions
    best_pred = min(results.values(), key=lambda x: x["metrics"]["mae"])["predictions"]
    compare_with_assumptions(y_test, best_pred, config)

    # Select best model
    best_model_name = select_best_model(results)
    best_result = results[best_model_name]

    # Save best model
    save_model(
        best_result["model"],
        None,  # LGD models don't need scaler for tree-based
        features,
        best_result["metrics"],
        best_model_name,
        config
    )

    # Log to MLflow
    log_to_mlflow(
        best_result["model"],
        best_result["metrics"],
        best_model_name,
        config,
        best_result.get("importance")
    )

    # Summary
    print("\n" + "=" * 60)
    print("Training Summary")
    print("=" * 60)

    print("\nModel Comparison:")
    print(f"  {'Model':<20} {'MAE':>8} {'RMSE':>8} {'R²':>8}")
    print("  " + "-" * 44)
    for name, result in results.items():
        m = result["metrics"]
        marker = " *" if name == best_model_name else ""
        print(f"  {name:<20} {m['mae']:>8.4f} {m['rmse']:>8.4f} {m['r2']:>8.4f}{marker}")

    print("\n* Selected as best model")

    print("\n" + "=" * 60)
    print("[SUCCESS] LGD model training completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Run 3_models/validate_models.py for validation")
    print("  2. Run 3_models/register_models.py to register in MLflow")
    print("  3. Run 4_endpoints/serve_pd.py to deploy models")

    return 0


if __name__ == "__main__":
    sys.exit(main())

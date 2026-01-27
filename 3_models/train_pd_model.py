#!/usr/bin/env python3
"""
PD (Probability of Default) Model Training Script
Trains and evaluates PD models using multiple algorithms.

Supports two data storage modes:
- local: Reads features from local parquet file (default)
- iceberg/cde/spark: Reads features from Iceberg tables via Spark
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
    from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import (
        roc_auc_score, roc_curve, precision_recall_curve,
        brier_score_loss, log_loss, classification_report,
        confusion_matrix
    )
    from sklearn.calibration import calibration_curve
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

# Get project root from environment or current working directory
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))

# Determine storage mode from environment
DATA_STORAGE_MODE = os.environ.get("DATA_STORAGE_MODE", "local").lower()


def load_config() -> dict:
    """Load PD model configuration."""
    config_path = PROJECT_ROOT / "3_models" / "configs" / "pd_config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_features_local(config: dict) -> pd.DataFrame:
    """Load feature matrix from local parquet file."""
    data_path = PROJECT_ROOT / "data" / "features" / "feature_matrix.parquet"

    if not data_path.exists():
        print(f"\n[ERROR] Feature matrix not found at {data_path}")
        print("Please run 2_features/feature_pipeline.py first")
        sys.exit(1)

    df = pd.read_parquet(data_path)
    print(f"\n[INFO] Loaded {len(df)} observations from local file")

    return df


def load_features_iceberg(config: dict) -> pd.DataFrame:
    """Load feature matrix from Iceberg tables via Spark."""
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        print("\n[ERROR] PySpark not available for Iceberg mode")
        print("Please install pyspark or use DATA_STORAGE_MODE=local")
        sys.exit(1)

    warehouse_path = os.environ.get("SPARK_WAREHOUSE_DIR")
    if not warehouse_path:
        print("\n[ERROR] SPARK_WAREHOUSE_DIR is required for Iceberg mode")
        print("Please set SPARK_WAREHOUSE_DIR or use DATA_STORAGE_MODE=local")
        sys.exit(1)

    features_path = f"{warehouse_path}/features"
    print(f"\n[INFO] Loading features from Iceberg: {features_path}")

    # Create Spark session (uses existing CML Spark config)
    spark = SparkSession.builder \
        .appName("PD_Model_Training") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()

    try:
        # Read features from Iceberg/parquet
        spark_df = spark.read.parquet(features_path)
        record_count = spark_df.count()
        print(f"[INFO] Found {record_count} records in Iceberg")

        # Convert to pandas for sklearn training
        df = spark_df.toPandas()
        print(f"[INFO] Loaded {len(df)} observations from Iceberg")

        return df
    except Exception as e:
        print(f"\n[ERROR] Failed to load features from Iceberg: {e}")
        print(f"  Path: {features_path}")
        print("  Please ensure feature engineering job has completed")
        sys.exit(1)
    finally:
        # Don't stop Spark session as it may be shared in CML
        pass


def load_features(config: dict) -> pd.DataFrame:
    """Load feature matrix based on DATA_STORAGE_MODE."""
    print(f"\n[INFO] Data storage mode: {DATA_STORAGE_MODE}")

    if DATA_STORAGE_MODE == "local":
        return load_features_local(config)
    elif DATA_STORAGE_MODE in ("iceberg", "cde", "spark"):
        return load_features_iceberg(config)
    else:
        print(f"\n[WARN] Unknown DATA_STORAGE_MODE: {DATA_STORAGE_MODE}, using local")
        return load_features_local(config)


def prepare_data(df: pd.DataFrame, config: dict) -> tuple:
    """Prepare data for training."""
    print("\n[INFO] Preparing data...")

    # Get feature list from config
    feature_list = config["features"]

    # Filter to available features
    available_features = [f for f in feature_list if f in df.columns]
    missing_features = [f for f in feature_list if f not in df.columns]

    if missing_features:
        print(f"  [WARN] Missing features: {missing_features}")

    print(f"  - Using {len(available_features)} features")

    # Create feature matrix
    X = df[available_features].copy()
    y = df["default_flag"].copy()

    # Handle missing values
    X = X.fillna(X.median())

    # Split data
    train_config = config["training"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=train_config["test_size"],
        random_state=train_config["random_state"],
        stratify=y if train_config["stratify"] else None
    )

    print(f"  - Train set: {len(X_train)} ({y_train.mean():.2%} default rate)")
    print(f"  - Test set: {len(X_test)} ({y_test.mean():.2%} default rate)")

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Convert back to DataFrame for feature names
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=available_features, index=X_train.index)
    X_test_scaled = pd.DataFrame(X_test_scaled, columns=available_features, index=X_test.index)

    return X_train, X_test, X_train_scaled, X_test_scaled, y_train, y_test, scaler, available_features


def calculate_gini(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Gini coefficient from AUC."""
    auc = roc_auc_score(y_true, y_pred)
    return 2 * auc - 1


def calculate_ks(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Kolmogorov-Smirnov statistic."""
    fpr, tpr, _ = roc_curve(y_true, y_pred)
    return max(tpr - fpr)


def evaluate_model(y_true: np.ndarray, y_pred_proba: np.ndarray, model_name: str) -> dict:
    """Evaluate model performance."""
    metrics = {
        "auc_roc": roc_auc_score(y_true, y_pred_proba),
        "gini": calculate_gini(y_true, y_pred_proba),
        "ks_statistic": calculate_ks(y_true, y_pred_proba),
        "brier_score": brier_score_loss(y_true, y_pred_proba),
        "log_loss": log_loss(y_true, y_pred_proba),
    }

    print(f"\n  {model_name} Metrics:")
    print(f"    AUC-ROC: {metrics['auc_roc']:.4f}")
    print(f"    Gini: {metrics['gini']:.4f}")
    print(f"    KS Statistic: {metrics['ks_statistic']:.4f}")
    print(f"    Brier Score: {metrics['brier_score']:.4f}")
    print(f"    Log Loss: {metrics['log_loss']:.4f}")

    return metrics


def train_logistic_regression(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    config: dict
) -> tuple:
    """Train Logistic Regression model."""
    print("\n[INFO] Training Logistic Regression...")

    params = config["hyperparameters"]["logistic"]

    model = LogisticRegression(
        C=params["C"],
        penalty=params["penalty"],
        solver=params["solver"],
        max_iter=params["max_iter"],
        class_weight=config["training"]["class_weight"],
        random_state=config["training"]["random_state"]
    )

    model.fit(X_train, y_train)

    # Predictions
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Evaluate
    metrics = evaluate_model(y_test, y_pred_proba, "Logistic Regression")

    return model, metrics, y_pred_proba


def train_gradient_boosting(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    config: dict
) -> tuple:
    """Train Gradient Boosting model."""
    print("\n[INFO] Training Gradient Boosting...")

    params = config["hyperparameters"]["gradient_boosting"]

    model = GradientBoostingClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        min_samples_split=params["min_samples_split"],
        min_samples_leaf=params["min_samples_leaf"],
        subsample=params["subsample"],
        random_state=config["training"]["random_state"]
    )

    model.fit(X_train, y_train)

    # Predictions
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Evaluate
    metrics = evaluate_model(y_test, y_pred_proba, "Gradient Boosting")

    return model, metrics, y_pred_proba


def train_xgboost(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    config: dict
) -> tuple:
    """Train XGBoost model."""
    print("\n[INFO] Training XGBoost...")

    params = config["hyperparameters"]["xgboost"]

    # Calculate scale_pos_weight for class imbalance
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1

    model = xgb.XGBClassifier(
        n_estimators=params["n_estimators"],
        max_depth=params["max_depth"],
        learning_rate=params["learning_rate"],
        min_child_weight=params["min_child_weight"],
        subsample=params["subsample"],
        colsample_bytree=params["colsample_bytree"],
        reg_alpha=params["reg_alpha"],
        reg_lambda=params["reg_lambda"],
        scale_pos_weight=scale_pos_weight,
        eval_metric=params["eval_metric"],
        random_state=config["training"]["random_state"],
        use_label_encoder=False
    )

    # Train with early stopping
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    # Predictions
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Evaluate
    metrics = evaluate_model(y_test, y_pred_proba, "XGBoost")

    # Feature importance
    importance = pd.DataFrame({
        "feature": X_train.columns,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)

    print("\n  Top 10 Features:")
    for _, row in importance.head(10).iterrows():
        bar = "█" * int(row["importance"] * 50)
        print(f"    {row['feature']:<30} {bar} {row['importance']:.4f}")

    return model, metrics, y_pred_proba, importance


def select_best_model(results: dict) -> str:
    """Select the best model based on AUC."""
    best_model = max(results.keys(), key=lambda k: results[k]["metrics"]["auc_roc"])
    best_auc = results[best_model]["metrics"]["auc_roc"]
    print(f"\n[INFO] Best model: {best_model} (AUC: {best_auc:.4f})")
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

    model_dir = PROJECT_ROOT / "data" / "models" / "pd"
    model_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = model_dir / f"pd_model_{model_name.lower().replace(' ', '_')}.pkl"
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
    latest_path = model_dir / "pd_model_latest.pkl"
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
    experiment_name = mlflow_config.get("experiment_name", "pd_model_training")

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=f"pd_{model_name.lower().replace(' ', '_')}"):
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

        # Log feature importance
        if feature_importance is not None:
            importance_path = Path("feature_importance.csv")
            feature_importance.to_csv(importance_path, index=False)
            mlflow.log_artifact(str(importance_path))
            importance_path.unlink()

        print(f"  - Logged run to {tracking_uri}")


def main():
    """Main function to train PD model."""
    print("\n" + "=" * 60)
    print("Credit Risk Platform - PD Model Training")
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

    # Logistic Regression (use scaled data)
    lr_model, lr_metrics, lr_pred = train_logistic_regression(
        X_train_scaled, X_test_scaled, y_train, y_test, config
    )
    results["Logistic Regression"] = {
        "model": lr_model,
        "metrics": lr_metrics,
        "predictions": lr_pred,
        "use_scaler": True
    }

    # Gradient Boosting (use unscaled data)
    gb_model, gb_metrics, gb_pred = train_gradient_boosting(
        X_train, X_test, y_train, y_test, config
    )
    results["Gradient Boosting"] = {
        "model": gb_model,
        "metrics": gb_metrics,
        "predictions": gb_pred,
        "use_scaler": False
    }

    # XGBoost (use unscaled data)
    xgb_model, xgb_metrics, xgb_pred, importance = train_xgboost(
        X_train, X_test, y_train, y_test, config
    )
    results["XGBoost"] = {
        "model": xgb_model,
        "metrics": xgb_metrics,
        "predictions": xgb_pred,
        "importance": importance,
        "use_scaler": False
    }

    # Select best model
    best_model_name = select_best_model(results)
    best_result = results[best_model_name]

    # Save best model
    use_scaler = best_result.get("use_scaler", False)
    model_scaler = scaler if use_scaler else None

    save_model(
        best_result["model"],
        model_scaler,
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
    print(f"  {'Model':<20} {'AUC':>8} {'Gini':>8} {'KS':>8}")
    print("  " + "-" * 44)
    for name, result in results.items():
        m = result["metrics"]
        marker = " *" if name == best_model_name else ""
        print(f"  {name:<20} {m['auc_roc']:>8.4f} {m['gini']:>8.4f} {m['ks_statistic']:>8.4f}{marker}")

    print("\n* Selected as best model")

    print("\n" + "=" * 60)
    print("[SUCCESS] PD model training completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Run 3_models/train_lgd_model.py to train LGD model")
    print("  2. Run 3_models/validate_models.py for validation")
    print("  3. Run 3_models/register_models.py to register in MLflow")

    return 0


if __name__ == "__main__":
    main()

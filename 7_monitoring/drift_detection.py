#!/usr/bin/env python3
"""
Model Drift Detection
Monitors for population and feature drift in credit risk models.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pickle

try:
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"[ERROR] Missing package: {e}")
    sys.exit(1)


PSI_THRESHOLD_WARN = 0.10
PSI_THRESHOLD_ALERT = 0.25


def get_paths():
    """Get project paths."""
    project_root = Path(__file__).parent.parent
    return {
        "db": project_root / "data" / "credit_risk.db",
        "features": project_root / "data" / "features" / "feature_matrix.parquet",
        "pd_model": project_root / "data" / "models" / "pd" / "pd_model_latest.pkl",
    }


def calculate_psi(baseline: np.ndarray, current: np.ndarray, n_bins: int = 10) -> float:
    """Calculate Population Stability Index."""
    if len(baseline) == 0 or len(current) == 0:
        return 0.0

    try:
        bins = pd.qcut(baseline, n_bins, duplicates='drop', retbins=True)[1]
    except ValueError:
        bins = np.linspace(baseline.min(), baseline.max(), n_bins + 1)

    baseline_dist = np.histogram(baseline, bins=bins)[0] / len(baseline)
    current_dist = np.histogram(current, bins=bins)[0] / len(current)

    baseline_dist = np.where(baseline_dist == 0, 0.0001, baseline_dist)
    current_dist = np.where(current_dist == 0, 0.0001, current_dist)

    psi = np.sum((current_dist - baseline_dist) * np.log(current_dist / baseline_dist))
    return psi


def load_baseline_predictions():
    """Load baseline predictions from training period."""
    paths = get_paths()

    # Load feature matrix as baseline
    if paths["features"].exists():
        df = pd.read_parquet(paths["features"])
        # Use first 70% as baseline
        n_baseline = int(len(df) * 0.7)
        return df.head(n_baseline)
    return None


def load_current_predictions(days: int = 30):
    """Load recent predictions."""
    paths = get_paths()

    if paths["db"].exists():
        conn = sqlite3.connect(str(paths["db"]))
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        query = f"""
            SELECT * FROM predictions
            WHERE predicted_at >= '{cutoff_date}'
        """
        try:
            df = pd.read_sql(query, conn)
            conn.close()
            return df
        except Exception:
            conn.close()
    return None


def detect_score_drift(baseline_scores: np.ndarray, current_scores: np.ndarray) -> dict:
    """Detect drift in PD score distribution."""
    psi = calculate_psi(baseline_scores, current_scores)

    if psi > PSI_THRESHOLD_ALERT:
        status = "ALERT"
    elif psi > PSI_THRESHOLD_WARN:
        status = "WARNING"
    else:
        status = "OK"

    return {
        "metric": "pd_score_psi",
        "value": round(psi, 4),
        "threshold_warn": PSI_THRESHOLD_WARN,
        "threshold_alert": PSI_THRESHOLD_ALERT,
        "status": status,
    }


def detect_feature_drift(baseline: pd.DataFrame, current: pd.DataFrame, features: list) -> list:
    """Detect drift in feature distributions."""
    results = []

    for feature in features:
        if feature in baseline.columns and feature in current.columns:
            base_vals = baseline[feature].dropna().values
            curr_vals = current[feature].dropna().values

            if len(base_vals) > 0 and len(curr_vals) > 0:
                psi = calculate_psi(base_vals, curr_vals)

                if psi > PSI_THRESHOLD_ALERT:
                    status = "ALERT"
                elif psi > PSI_THRESHOLD_WARN:
                    status = "WARNING"
                else:
                    status = "OK"

                results.append({
                    "feature": feature,
                    "psi": round(psi, 4),
                    "status": status,
                })

    return sorted(results, key=lambda x: x["psi"], reverse=True)


def save_monitoring_result(result: dict, conn: sqlite3.Connection):
    """Save monitoring result to database."""
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO monitoring (
            model_name, monitoring_date, psi_score, csi_scores_json,
            alert_triggered, alert_message
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        result.get("model_name", "pd_model"),
        datetime.now().strftime("%Y-%m-%d"),
        result.get("psi_score"),
        str(result.get("feature_drift", [])),
        1 if result.get("alert_triggered") else 0,
        result.get("alert_message"),
    ))

    conn.commit()


def run_drift_detection():
    """Run drift detection for all models."""
    print("\n" + "=" * 60)
    print("Model Drift Detection")
    print("=" * 60)

    paths = get_paths()

    # Load baseline
    baseline = load_baseline_predictions()
    if baseline is None:
        print("[WARN] No baseline data available")
        return

    # For demo, use last 30% as current
    n_current = int(len(baseline) * 0.3)
    current = baseline.tail(n_current)
    baseline = baseline.head(len(baseline) - n_current)

    print(f"\nBaseline period: {len(baseline)} observations")
    print(f"Current period: {len(current)} observations")

    # Detect score drift
    if "pd_score" not in baseline.columns:
        # Simulate scores
        baseline["pd_score"] = np.random.uniform(0, 0.2, len(baseline))
        current["pd_score"] = np.random.uniform(0.01, 0.22, len(current))

    score_drift = detect_score_drift(
        baseline["pd_score"].values,
        current["pd_score"].values
    )

    print(f"\nScore Distribution Drift:")
    print(f"  PSI: {score_drift['value']} [{score_drift['status']}]")

    # Detect feature drift
    key_features = [
        "debt_to_equity", "current_ratio", "interest_coverage_ratio",
        "credit_score_normalized", "utilization_rate"
    ]
    feature_drift = detect_feature_drift(baseline, current, key_features)

    print(f"\nFeature Drift (Top 5):")
    for fd in feature_drift[:5]:
        print(f"  {fd['feature']}: PSI={fd['psi']} [{fd['status']}]")

    # Determine if alert needed
    alert_triggered = score_drift["status"] == "ALERT"
    alert_features = [f for f in feature_drift if f["status"] == "ALERT"]

    result = {
        "model_name": "pd_model",
        "psi_score": score_drift["value"],
        "feature_drift": feature_drift,
        "alert_triggered": alert_triggered or len(alert_features) > 0,
        "alert_message": None,
    }

    if alert_triggered:
        result["alert_message"] = f"PSI={score_drift['value']} exceeds threshold"
    elif alert_features:
        result["alert_message"] = f"{len(alert_features)} features with drift alert"

    # Save to database
    if paths["db"].exists():
        conn = sqlite3.connect(str(paths["db"]))
        save_monitoring_result(result, conn)
        conn.close()
        print(f"\n[INFO] Results saved to monitoring table")

    # Summary
    print("\n" + "=" * 60)
    print("Drift Detection Summary")
    print("=" * 60)

    if result["alert_triggered"]:
        print(f"\n[ALERT] {result['alert_message']}")
        print("Action: Consider model recalibration")
    else:
        print("\n[OK] No significant drift detected")

    return result


if __name__ == "__main__":
    run_drift_detection()

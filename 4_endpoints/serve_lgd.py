#!/usr/bin/env python3
"""
CML Model Endpoint for LGD (Loss Given Default)
Serves the trained LGD model for real-time predictions.
"""

import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Global model variable
_model_artifact = None

# LGD assumptions by collateral type (fallback)
LGD_ASSUMPTIONS = {
    "real_estate": 0.35,
    "equipment": 0.45,
    "inventory": 0.55,
    "receivables": 0.55,
    "securities": 0.40,
    "unsecured": 0.75,
}


def load_model():
    """Load the LGD model artifact."""
    global _model_artifact

    if _model_artifact is not None:
        return _model_artifact

    project_root = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
    possible_paths = [
        project_root / "data" / "models" / "lgd" / "lgd_model_latest.pkl",
        Path("/home/cdsw/data/models/lgd/lgd_model_latest.pkl"),
        Path("./data/models/lgd/lgd_model_latest.pkl"),
    ]

    model_path = None
    for path in possible_paths:
        if path.exists():
            model_path = path
            break

    if model_path is None:
        print("[WARN] LGD model not found, using assumptions")
        return None

    with open(model_path, "rb") as f:
        _model_artifact = pickle.load(f)

    print(f"[INFO] Loaded LGD model from {model_path}")

    return _model_artifact


def get_lgd_assumption(collateral_type: str) -> float:
    """Get LGD assumption based on collateral type."""
    return LGD_ASSUMPTIONS.get(collateral_type.lower(), 0.75)


def preprocess_features(features: dict, model_artifact: dict) -> pd.DataFrame:
    """Preprocess input features for prediction."""
    required_features = model_artifact["features"]

    feature_values = {}
    for feat in required_features:
        if feat in features:
            feature_values[feat] = [features[feat]]
        else:
            feature_values[feat] = [np.nan]

    df = pd.DataFrame(feature_values)
    df = df.fillna(0)

    return df


def predict(args: dict) -> dict:
    """
    Main prediction function for CML endpoint.

    Args:
        args: Dictionary containing:
            - collateral_type: str
            - ltv_ratio: float
            - loan_to_revenue_ratio: float
            - debt_to_equity: float
            - credit_score_normalized: float
            ... other features

    Returns:
        Dictionary with prediction results:
            - lgd_score: float (0-1)
            - lgd_source: str (model or assumption)
            - expected_recovery_rate: float
    """
    try:
        model_artifact = load_model()

        collateral_type = args.get("collateral_type", "unsecured")

        if model_artifact is None:
            # Use fixed assumptions
            lgd_score = get_lgd_assumption(collateral_type)
            lgd_source = "assumption"
        else:
            # Use model prediction
            model = model_artifact["model"]
            features_df = preprocess_features(args, model_artifact)

            lgd_score = model.predict(features_df)[0]
            lgd_score = np.clip(lgd_score, 0, 1)
            lgd_source = "model"

        expected_recovery_rate = 1 - lgd_score

        return {
            "status": "success",
            "lgd_score": round(float(lgd_score), 6),
            "lgd_source": lgd_source,
            "expected_recovery_rate": round(float(expected_recovery_rate), 6),
            "collateral_type": collateral_type,
            "assumption_lgd": get_lgd_assumption(collateral_type),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "lgd_score": None,
        }


if __name__ == "__main__":
    test_features = {
        "collateral_type": "equipment",
        "ltv_ratio": 0.7,
        "debt_to_equity": 1.5,
        "current_ratio": 1.8,
        "interest_coverage_ratio": 4.5,
        "credit_score_normalized": 0.75,
        "utilization_rate": 0.4,
        "loan_to_revenue_ratio": 0.15,
        "loan_to_assets_ratio": 0.10,
        "term_months": 36,
        "interest_rate": 0.065,
        "industry_risk_tier": 3,
    }

    print("\n" + "=" * 50)
    print("LGD Model Endpoint - Test")
    print("=" * 50)

    result = predict(test_features)

    print(f"\nPrediction Results:")
    print(f"  Status: {result['status']}")
    print(f"  LGD Score: {result['lgd_score']}")
    print(f"  Source: {result['lgd_source']}")
    print(f"  Expected Recovery Rate: {result['expected_recovery_rate']}")

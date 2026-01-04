#!/usr/bin/env python3
"""
CML Model Endpoint for PD (Probability of Default)
Serves the trained PD model for real-time predictions.
"""

import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Global model variable (loaded once)
_model_artifact = None


def load_model():
    """Load the PD model artifact."""
    global _model_artifact

    if _model_artifact is not None:
        return _model_artifact

    # Try different paths for CML and local development
    possible_paths = [
        Path(__file__).parent.parent / "data" / "models" / "pd" / "pd_model_latest.pkl",
        Path("/home/cdsw/data/models/pd/pd_model_latest.pkl"),
        Path("./data/models/pd/pd_model_latest.pkl"),
    ]

    model_path = None
    for path in possible_paths:
        if path.exists():
            model_path = path
            break

    if model_path is None:
        raise FileNotFoundError("PD model not found. Please train the model first.")

    with open(model_path, "rb") as f:
        _model_artifact = pickle.load(f)

    print(f"[INFO] Loaded PD model from {model_path}")
    print(f"[INFO] Model type: {_model_artifact.get('model_name', 'unknown')}")
    print(f"[INFO] Features: {len(_model_artifact['features'])}")

    return _model_artifact


def preprocess_features(features: dict, model_artifact: dict) -> pd.DataFrame:
    """Preprocess input features for prediction."""
    required_features = model_artifact["features"]

    # Create DataFrame with required features
    feature_values = {}
    for feat in required_features:
        if feat in features:
            feature_values[feat] = [features[feat]]
        else:
            feature_values[feat] = [np.nan]

    df = pd.DataFrame(feature_values)

    # Handle missing values with median (from training)
    df = df.fillna(0)  # Simple imputation for missing

    # Apply scaler if present
    scaler = model_artifact.get("scaler")
    if scaler is not None:
        scaled_values = scaler.transform(df)
        df = pd.DataFrame(scaled_values, columns=required_features)

    return df


def get_risk_grade(pd_score: float) -> str:
    """Convert PD score to risk grade."""
    grades = [
        (0.005, "AAA"),
        (0.01, "AA"),
        (0.02, "A"),
        (0.03, "BBB"),
        (0.05, "BB"),
        (0.10, "B"),
        (0.15, "CCC"),
        (0.25, "CC"),
        (0.50, "C"),
        (1.0, "D"),
    ]

    for threshold, grade in grades:
        if pd_score <= threshold:
            return grade

    return "D"


def get_decision(pd_score: float) -> str:
    """Get decision recommendation based on PD score."""
    if pd_score < 0.03:
        return "AUTO_APPROVE"
    elif pd_score < 0.10:
        return "REFER"
    elif pd_score < 0.15:
        return "ENHANCED_REVIEW"
    else:
        return "AUTO_DECLINE"


def predict(args: dict) -> dict:
    """
    Main prediction function for CML endpoint.

    Args:
        args: Dictionary containing customer features:
            - debt_to_equity: float
            - current_ratio: float
            - interest_coverage_ratio: float
            - credit_score_normalized: float (0-1)
            - avg_days_past_due: float
            - industry_risk_tier: int (1-5)
            - loan_to_revenue_ratio: float
            ... and other features

    Returns:
        Dictionary with prediction results:
            - pd_score: float (0-1)
            - risk_grade: str
            - decision: str
            - confidence: float
    """
    try:
        # Load model
        model_artifact = load_model()
        model = model_artifact["model"]

        # Preprocess features
        features_df = preprocess_features(args, model_artifact)

        # Make prediction
        pd_score = model.predict_proba(features_df)[0, 1]

        # Get additional outputs
        risk_grade = get_risk_grade(pd_score)
        decision = get_decision(pd_score)

        # Calculate confidence (based on distance from decision boundaries)
        if pd_score < 0.03:
            confidence = min(1.0, (0.03 - pd_score) / 0.03 * 0.5 + 0.5)
        elif pd_score > 0.15:
            confidence = min(1.0, (pd_score - 0.15) / 0.85 * 0.5 + 0.5)
        else:
            # In referral zone, lower confidence
            confidence = 0.5 + abs(pd_score - 0.09) / 0.12 * 0.3

        return {
            "status": "success",
            "pd_score": round(float(pd_score), 6),
            "risk_grade": risk_grade,
            "decision": decision,
            "confidence": round(confidence, 4),
            "model_version": model_artifact.get("trained_at", "unknown"),
            "features_used": len(model_artifact["features"]),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "pd_score": None,
            "risk_grade": None,
            "decision": None,
        }


# For local testing
if __name__ == "__main__":
    # Sample test input
    test_features = {
        "debt_to_equity": 1.5,
        "debt_to_assets": 0.6,
        "current_ratio": 1.8,
        "quick_ratio": 1.2,
        "interest_coverage_ratio": 4.5,
        "return_on_assets": 0.08,
        "return_on_equity": 0.15,
        "profit_margin": 0.10,
        "credit_score_normalized": 0.75,
        "payment_index_trend": 5.0,
        "utilization_rate": 0.4,
        "derogatory_ratio": 0.01,
        "avg_days_past_due": 2.5,
        "max_days_past_due": 15,
        "dpd_volatility": 5.0,
        "count_30dpd": 1,
        "count_60dpd": 0,
        "count_90dpd": 0,
        "payment_consistency_score": 0.95,
        "loan_to_revenue_ratio": 0.15,
        "loan_to_assets_ratio": 0.10,
        "industry_default_rate": 0.04,
        "industry_risk_tier": 3,
    }

    print("\n" + "=" * 50)
    print("PD Model Endpoint - Test")
    print("=" * 50)

    result = predict(test_features)

    print(f"\nInput Features: {len(test_features)}")
    print(f"\nPrediction Results:")
    print(f"  Status: {result['status']}")
    print(f"  PD Score: {result['pd_score']}")
    print(f"  Risk Grade: {result['risk_grade']}")
    print(f"  Decision: {result['decision']}")
    print(f"  Confidence: {result['confidence']}")

#!/usr/bin/env python3
"""
CML Model Endpoint for PD (Probability of Default)
Ready for deployment as Cloudera ML Model Endpoint.

Deployment:
1. Create a new Model in CML
2. Set this file as the entry point
3. Set function name: predict
4. Configure resources (CPU/Memory)
5. Deploy
"""

import os
import sys
import pickle
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import numpy as np
import pandas as pd

# CML-specific imports (available in CML environment)
try:
    import cml.decorators as cml
    CML_AVAILABLE = True
except ImportError:
    CML_AVAILABLE = False
    # Mock decorator for local development
    class cml:
        @staticmethod
        def model(*args, **kwargs):
            def decorator(func):
                return func
            return decorator


# =============================================================================
# Model Configuration
# =============================================================================

MODEL_NAME = "pd_model"
MODEL_VERSION = os.environ.get("MODEL_VERSION", "1.0")

# Model paths - CML uses /home/cdsw as project root
_env_model_path = os.environ.get("PD_MODEL_PATH", "")
_project_root = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
MODEL_PATHS = [
    Path(_env_model_path) if _env_model_path else None,
    Path("/home/cdsw/data/models/pd/pd_model_latest.pkl"),
    _project_root / "data" / "models" / "pd" / "pd_model_latest.pkl",
    Path("./data/models/pd/pd_model_latest.pkl"),
]

# Global model cache
_model_artifact: Optional[Dict] = None
_model_loaded_at: Optional[str] = None


# =============================================================================
# Model Loading
# =============================================================================

def load_model() -> Dict:
    """Load the PD model artifact with caching."""
    global _model_artifact, _model_loaded_at

    if _model_artifact is not None:
        return _model_artifact

    model_path = None
    for path in MODEL_PATHS:
        if path and path.exists() and path.is_file():
            model_path = path
            break

    if model_path is None:
        raise FileNotFoundError(
            f"PD model not found. Searched paths: {[str(p) for p in MODEL_PATHS if p]}"
        )

    with open(model_path, "rb") as f:
        _model_artifact = pickle.load(f)

    _model_loaded_at = datetime.now().isoformat()

    print(f"[PD_MODEL] Loaded from {model_path}")
    print(f"[PD_MODEL] Type: {_model_artifact.get('model_type', 'unknown')}")
    print(f"[PD_MODEL] Features: {len(_model_artifact.get('features', []))}")
    print(f"[PD_MODEL] Trained: {_model_artifact.get('trained_at', 'unknown')}")

    return _model_artifact


# =============================================================================
# Feature Engineering
# =============================================================================

def prepare_features(input_data: Dict, model_artifact: Dict) -> pd.DataFrame:
    """
    Prepare input features for model prediction.
    Handles missing values and applies scaling if available.
    """
    required_features = model_artifact.get("features", [])

    # Build feature vector
    feature_values = {}
    for feat in required_features:
        value = input_data.get(feat)
        if value is not None:
            feature_values[feat] = [float(value)]
        else:
            # Use default/median from training if available
            defaults = model_artifact.get("feature_defaults", {})
            feature_values[feat] = [defaults.get(feat, 0.0)]

    df = pd.DataFrame(feature_values)

    # Apply scaler if present
    scaler = model_artifact.get("scaler")
    if scaler is not None:
        try:
            scaled = scaler.transform(df[required_features])
            df = pd.DataFrame(scaled, columns=required_features)
        except Exception as e:
            print(f"[PD_MODEL] Scaler warning: {e}")

    return df


def get_risk_grade(pd_score: float) -> str:
    """Convert PD score to risk grade (S&P-like scale)."""
    thresholds = [
        (0.0003, "AAA"), (0.001, "AA+"), (0.002, "AA"), (0.003, "AA-"),
        (0.005, "A+"), (0.007, "A"), (0.01, "A-"),
        (0.015, "BBB+"), (0.02, "BBB"), (0.03, "BBB-"),
        (0.04, "BB+"), (0.05, "BB"), (0.07, "BB-"),
        (0.10, "B+"), (0.13, "B"), (0.17, "B-"),
        (0.22, "CCC+"), (0.30, "CCC"), (0.40, "CCC-"),
        (0.50, "CC"), (0.70, "C"), (1.0, "D"),
    ]
    for threshold, grade in thresholds:
        if pd_score <= threshold:
            return grade
    return "D"


def get_decision_recommendation(pd_score: float, rorac: float = None) -> Dict:
    """Get decision recommendation based on PD and RORAC."""
    if pd_score < 0.02:
        decision = "AUTO_APPROVE"
        confidence = "HIGH"
    elif pd_score < 0.05:
        decision = "APPROVE"
        confidence = "MEDIUM"
    elif pd_score < 0.10:
        decision = "REFER"
        confidence = "LOW"
    elif pd_score < 0.15:
        decision = "ENHANCED_REVIEW"
        confidence = "LOW"
    else:
        decision = "DECLINE"
        confidence = "HIGH"

    # Adjust based on RORAC if provided
    if rorac is not None:
        if rorac < 0.08 and decision in ["AUTO_APPROVE", "APPROVE"]:
            decision = "REFER"
            confidence = "MEDIUM"
        elif rorac > 0.20 and decision == "REFER":
            decision = "APPROVE"
            confidence = "MEDIUM"

    return {"decision": decision, "confidence": confidence}


# =============================================================================
# CML Model Endpoint
# =============================================================================

@cml.model(name=MODEL_NAME, version=MODEL_VERSION)
def predict(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    CML Model Endpoint for PD prediction.

    Input Schema:
    {
        "debt_to_equity": float,
        "current_ratio": float,
        "interest_coverage_ratio": float,
        "credit_score_normalized": float,  # 0-1 scale
        "utilization_rate": float,
        "industry_risk_tier": int,  # 1-5
        "loan_to_revenue_ratio": float,
        "years_in_business": int,
        ... (see full feature list in model artifact)
    }

    Output Schema:
    {
        "status": "success" | "error",
        "pd_score": float,  # Probability of default (0-1)
        "risk_grade": str,  # S&P-like grade (AAA to D)
        "decision": str,    # AUTO_APPROVE, APPROVE, REFER, ENHANCED_REVIEW, DECLINE
        "confidence": str,  # HIGH, MEDIUM, LOW
        "model_version": str,
        "timestamp": str
    }
    """
    timestamp = datetime.now().isoformat()

    try:
        # Load model
        model_artifact = load_model()
        model = model_artifact["model"]

        # Prepare features
        features_df = prepare_features(args, model_artifact)

        # Predict probability of default
        if hasattr(model, "predict_proba"):
            pd_score = float(model.predict_proba(features_df)[0, 1])
        else:
            # Regression model output
            pd_score = float(model.predict(features_df)[0])
            pd_score = np.clip(pd_score, 0, 1)

        # Get risk grade and decision
        risk_grade = get_risk_grade(pd_score)
        recommendation = get_decision_recommendation(pd_score)

        return {
            "status": "success",
            "pd_score": round(pd_score, 6),
            "risk_grade": risk_grade,
            "decision": recommendation["decision"],
            "confidence": recommendation["confidence"],
            "model_version": str(model_artifact.get("trained_at", MODEL_VERSION)),
            "model_type": model_artifact.get("model_type", "unknown"),
            "features_used": len(model_artifact.get("features", [])),
            "timestamp": timestamp,
        }

    except FileNotFoundError as e:
        return {
            "status": "error",
            "error_type": "model_not_found",
            "error": str(e),
            "pd_score": None,
            "risk_grade": None,
            "decision": None,
            "timestamp": timestamp,
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "prediction_error",
            "error": str(e),
            "pd_score": None,
            "risk_grade": None,
            "decision": None,
            "timestamp": timestamp,
        }


def health_check() -> Dict[str, Any]:
    """Health check endpoint for CML model monitoring."""
    try:
        model_artifact = load_model()
        return {
            "status": "healthy",
            "model_name": MODEL_NAME,
            "model_version": str(model_artifact.get("trained_at", MODEL_VERSION)),
            "model_loaded_at": _model_loaded_at,
            "features_count": len(model_artifact.get("features", [])),
            "metrics": model_artifact.get("metrics", {}),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# =============================================================================
# Local Testing
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PD Model Endpoint - Local Test")
    print("=" * 60)

    # Health check
    print("\n[Health Check]")
    health = health_check()
    print(json.dumps(health, indent=2, default=str))

    # Test prediction
    test_input = {
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

    print("\n[Prediction Test]")
    print(f"Input features: {len(test_input)}")

    result = predict(test_input)
    print(json.dumps(result, indent=2, default=str))

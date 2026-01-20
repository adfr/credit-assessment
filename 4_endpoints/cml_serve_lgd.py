#!/usr/bin/env python3
"""
CML Model Endpoint for LGD (Loss Given Default)
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
    import cml.models_v1 as models
    CML_AVAILABLE = True
except ImportError:
    CML_AVAILABLE = False
    # Mock decorator for local development
    class models:
        @staticmethod
        def cml_model(func):
            return func


# =============================================================================
# Model Configuration
# =============================================================================

MODEL_NAME = "lgd_model"
MODEL_VERSION = os.environ.get("MODEL_VERSION", "1.0")

# Model paths - CML uses /home/cdsw as project root
_env_model_path = os.environ.get("LGD_MODEL_PATH", "")
_project_root = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
MODEL_PATHS = [
    Path(_env_model_path) if _env_model_path else None,
    Path("/home/cdsw/data/models/lgd/lgd_model_latest.pkl"),
    _project_root / "data" / "models" / "lgd" / "lgd_model_latest.pkl",
    Path("./data/models/lgd/lgd_model_latest.pkl"),
]

# LGD assumptions by collateral type (regulatory/industry standards)
LGD_ASSUMPTIONS = {
    "cash": 0.0,
    "government_securities": 0.05,
    "investment_grade_bonds": 0.15,
    "real_estate_commercial": 0.30,
    "real_estate_residential": 0.25,
    "real_estate": 0.30,
    "equipment_heavy": 0.40,
    "equipment": 0.45,
    "vehicles": 0.50,
    "inventory": 0.55,
    "receivables": 0.55,
    "securities": 0.35,
    "personal_guarantee": 0.65,
    "unsecured": 0.75,
    "subordinated": 0.85,
}

# Global model cache
_model_artifact: Optional[Dict] = None
_model_loaded_at: Optional[str] = None


# =============================================================================
# Model Loading
# =============================================================================

def load_model() -> Optional[Dict]:
    """Load the LGD model artifact with caching."""
    global _model_artifact, _model_loaded_at

    if _model_artifact is not None:
        return _model_artifact

    model_path = None
    for path in MODEL_PATHS:
        if path and path.exists() and path.is_file():
            model_path = path
            break

    if model_path is None:
        print("[LGD_MODEL] Model not found, will use assumptions")
        return None

    with open(model_path, "rb") as f:
        _model_artifact = pickle.load(f)

    _model_loaded_at = datetime.now().isoformat()

    print(f"[LGD_MODEL] Loaded from {model_path}")
    print(f"[LGD_MODEL] Type: {_model_artifact.get('model_type', 'unknown')}")
    print(f"[LGD_MODEL] Features: {len(_model_artifact.get('features', []))}")
    print(f"[LGD_MODEL] Trained: {_model_artifact.get('trained_at', 'unknown')}")

    return _model_artifact


# =============================================================================
# Feature Engineering
# =============================================================================

def prepare_features(input_data: Dict, model_artifact: Dict) -> pd.DataFrame:
    """
    Prepare input features for model prediction.
    """
    required_features = model_artifact.get("features", [])

    feature_values = {}
    for feat in required_features:
        value = input_data.get(feat)
        if value is not None:
            feature_values[feat] = [float(value)]
        else:
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
            print(f"[LGD_MODEL] Scaler warning: {e}")

    return df


def get_lgd_assumption(collateral_type: str, ltv_ratio: float = None) -> float:
    """
    Get LGD assumption based on collateral type and LTV.
    Applies haircuts based on loan-to-value ratio.
    """
    base_lgd = LGD_ASSUMPTIONS.get(collateral_type.lower(), 0.75)

    # Apply LTV adjustment if provided
    if ltv_ratio is not None and ltv_ratio > 0:
        if ltv_ratio > 1.0:
            # Underwater - increase LGD
            base_lgd = min(1.0, base_lgd + (ltv_ratio - 1.0) * 0.5)
        elif ltv_ratio < 0.6:
            # Well-secured - decrease LGD
            base_lgd = max(0.05, base_lgd * 0.8)

    return base_lgd


def calculate_expected_recovery(lgd: float, loan_amount: float = None) -> Dict:
    """Calculate expected recovery metrics."""
    recovery_rate = 1 - lgd

    result = {
        "recovery_rate": round(recovery_rate, 4),
        "lgd_percentage": round(lgd * 100, 2),
    }

    if loan_amount:
        result["expected_loss_amount"] = round(lgd * loan_amount, 2)
        result["expected_recovery_amount"] = round(recovery_rate * loan_amount, 2)

    return result


# =============================================================================
# CML Model Endpoint
# =============================================================================

@models.cml_model
def predict(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    CML Model Endpoint for LGD prediction.

    Input Schema:
    {
        "collateral_type": str,  # real_estate, equipment, unsecured, etc.
        "ltv_ratio": float,      # Loan-to-value ratio (0-2+)
        "loan_amount": float,    # Optional: for expected loss calculation
        "debt_to_equity": float,
        "current_ratio": float,
        "interest_coverage_ratio": float,
        "credit_score_normalized": float,
        "utilization_rate": float,
        "industry_risk_tier": int,
        ... (see full feature list in model artifact)
    }

    Output Schema:
    {
        "status": "success" | "error",
        "lgd_score": float,      # Loss Given Default (0-1)
        "lgd_source": str,       # "model" or "assumption"
        "recovery_rate": float,  # Expected recovery (0-1)
        "expected_loss_amount": float,  # If loan_amount provided
        "model_version": str,
        "timestamp": str
    }
    """
    timestamp = datetime.now().isoformat()

    try:
        model_artifact = load_model()

        collateral_type = args.get("collateral_type", "unsecured")
        ltv_ratio = args.get("ltv_ratio")
        loan_amount = args.get("loan_amount")

        if model_artifact is None:
            # Use regulatory assumptions
            lgd_score = get_lgd_assumption(collateral_type, ltv_ratio)
            lgd_source = "assumption"
            model_version = "assumption_v1"
        else:
            # Use trained model
            model = model_artifact["model"]
            features_df = prepare_features(args, model_artifact)

            lgd_score = float(model.predict(features_df)[0])
            lgd_score = np.clip(lgd_score, 0, 1)
            lgd_source = "model"
            model_version = str(model_artifact.get("trained_at", MODEL_VERSION))

        # Calculate recovery metrics
        recovery_metrics = calculate_expected_recovery(lgd_score, loan_amount)

        # Get assumption for comparison
        assumption_lgd = get_lgd_assumption(collateral_type, ltv_ratio)

        return {
            "status": "success",
            "lgd_score": round(lgd_score, 6),
            "lgd_source": lgd_source,
            "recovery_rate": recovery_metrics["recovery_rate"],
            "lgd_percentage": recovery_metrics["lgd_percentage"],
            "expected_loss_amount": recovery_metrics.get("expected_loss_amount"),
            "expected_recovery_amount": recovery_metrics.get("expected_recovery_amount"),
            "collateral_type": collateral_type,
            "ltv_ratio": ltv_ratio,
            "assumption_lgd": round(assumption_lgd, 4),
            "model_version": model_version,
            "model_type": model_artifact.get("model_type", "assumption") if model_artifact else "assumption",
            "timestamp": timestamp,
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": "prediction_error",
            "error": str(e),
            "lgd_score": None,
            "recovery_rate": None,
            "timestamp": timestamp,
        }


def health_check() -> Dict[str, Any]:
    """Health check endpoint for CML model monitoring."""
    try:
        model_artifact = load_model()
        if model_artifact:
            return {
                "status": "healthy",
                "model_name": MODEL_NAME,
                "model_version": str(model_artifact.get("trained_at", MODEL_VERSION)),
                "model_loaded_at": _model_loaded_at,
                "features_count": len(model_artifact.get("features", [])),
                "metrics": model_artifact.get("metrics", {}),
                "using_model": True,
            }
        else:
            return {
                "status": "healthy",
                "model_name": MODEL_NAME,
                "model_version": "assumption_v1",
                "using_model": False,
                "note": "Using regulatory LGD assumptions",
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
    print("LGD Model Endpoint - Local Test")
    print("=" * 60)

    # Health check
    print("\n[Health Check]")
    health = health_check()
    print(json.dumps(health, indent=2, default=str))

    # Test different collateral types
    test_cases = [
        {"collateral_type": "real_estate", "ltv_ratio": 0.7, "loan_amount": 1000000},
        {"collateral_type": "equipment", "ltv_ratio": 0.8, "loan_amount": 500000},
        {"collateral_type": "unsecured", "loan_amount": 250000},
    ]

    for i, test_input in enumerate(test_cases):
        print(f"\n[Test Case {i+1}]")
        print(f"Collateral: {test_input['collateral_type']}, LTV: {test_input.get('ltv_ratio', 'N/A')}")

        # Add standard features
        test_input.update({
            "debt_to_equity": 1.5,
            "current_ratio": 1.8,
            "interest_coverage_ratio": 4.5,
            "credit_score_normalized": 0.75,
            "utilization_rate": 0.4,
            "industry_risk_tier": 3,
        })

        result = predict(test_input)
        print(json.dumps(result, indent=2, default=str))

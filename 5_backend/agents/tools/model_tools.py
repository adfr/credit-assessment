"""
Model Tools
Tools for calling ML model endpoints.
"""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "4_endpoints"))


def call_pd_model(features: dict) -> dict:
    """
    Call the PD (Probability of Default) model endpoint.

    Args:
        features: Dictionary containing model features

    Returns:
        Dictionary with pd_score, risk_grade, and confidence
    """
    try:
        from serve_pd import predict
        result = predict(features)
        return {
            "status": "success",
            "pd_score": result.get("pd_score"),
            "risk_grade": result.get("risk_grade"),
            "confidence": result.get("confidence", 0.85),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "pd_score": None,
        }


def call_lgd_model(features: dict) -> dict:
    """
    Call the LGD (Loss Given Default) model endpoint.

    Args:
        features: Dictionary containing model features including collateral info

    Returns:
        Dictionary with lgd_score and recovery_rate
    """
    try:
        from serve_lgd import predict
        result = predict(features)
        return {
            "status": "success",
            "lgd_score": result.get("lgd_score"),
            "recovery_rate": result.get("recovery_rate"),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "lgd_score": None,
        }


def call_risk_engine(features: dict, loan_params: dict) -> dict:
    """
    Call the risk engine for comprehensive risk assessment.

    Args:
        features: Dictionary containing model features
        loan_params: Dictionary with loan parameters (amount, term, rate)

    Returns:
        Dictionary with complete risk metrics
    """
    try:
        from serve_risk_engine import score

        args = {**features, **loan_params}
        result = score(args)

        return {
            "status": "success",
            "pd_score": result.get("pd_score"),
            "lgd_score": result.get("lgd_score"),
            "ead": result.get("ead"),
            "expected_loss": result.get("expected_loss"),
            "unexpected_loss": result.get("unexpected_loss"),
            "economic_capital": result.get("economic_capital"),
            "regulatory_capital": result.get("regulatory_capital"),
            "rorac": result.get("rorac"),
            "risk_grade": result.get("risk_grade"),
            "pricing_recommendation": result.get("pricing_recommendation"),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def prepare_model_features(customer_data: dict, bureau_data: dict) -> dict:
    """
    Prepare features for model input from customer and bureau data.

    Args:
        customer_data: Customer financial information
        bureau_data: Bureau/credit report data

    Returns:
        Dictionary with computed features
    """
    features = {}

    # Financial ratios
    total_assets = customer_data.get("total_assets", 1)
    total_liabilities = customer_data.get("total_liabilities", 0)
    equity = total_assets - total_liabilities

    features["debt_to_equity"] = total_liabilities / max(equity, 1)
    features["debt_to_assets"] = total_liabilities / max(total_assets, 1)
    features["current_ratio"] = customer_data.get("current_ratio", 1.5)
    features["quick_ratio"] = customer_data.get("quick_ratio", 1.0)
    features["interest_coverage_ratio"] = customer_data.get("interest_coverage_ratio", 3.0)

    # Profitability
    revenue = customer_data.get("annual_revenue", 1)
    net_income = customer_data.get("net_income", 0)
    features["return_on_assets"] = net_income / max(total_assets, 1)
    features["return_on_equity"] = net_income / max(equity, 1)
    features["profit_margin"] = net_income / max(revenue, 1)

    # Bureau features
    features["credit_score_normalized"] = bureau_data.get("credit_score", 70) / 100
    features["utilization_rate"] = bureau_data.get("utilization_rate", 0.5)
    features["derogatory_ratio"] = bureau_data.get("derogatory_count", 0) / 12

    # Industry
    features["industry_default_rate"] = bureau_data.get("industry_default_rate", 0.04)
    features["industry_risk_tier"] = bureau_data.get("industry_risk_tier", 3)

    return features

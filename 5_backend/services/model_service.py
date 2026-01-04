"""
Model Service
Handles ML model predictions for PD, LGD, and risk scoring.
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "4_endpoints"))


class ModelService:
    """Service for ML model operations."""

    def __init__(self):
        self.pd_endpoint = None
        self.lgd_endpoint = None
        self.risk_engine_endpoint = None

    async def predict_pd(self, features: dict) -> dict:
        """Get probability of default prediction."""
        try:
            from serve_pd import predict
            return predict(features)
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "pd_score": None,
            }

    async def predict_lgd(self, features: dict) -> dict:
        """Get loss given default prediction."""
        try:
            from serve_lgd import predict
            return predict(features)
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "lgd_score": None,
            }

    async def score_risk(self, features: dict, loan_params: dict) -> dict:
        """Get complete risk assessment."""
        try:
            from serve_risk_engine import score

            # Merge features and loan params
            args = {**features, **loan_params}
            return score(args)

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    async def get_risk_grade(self, pd_score: float) -> str:
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

    async def get_decision_recommendation(
        self,
        pd_score: float,
        rorac: float,
        compliance_passed: bool = True
    ) -> dict:
        """Get decision recommendation based on scores."""
        if not compliance_passed:
            return {
                "decision": "DECLINE",
                "reason": "Failed compliance checks",
                "auto_decidable": True,
            }

        if pd_score < 0.03 and rorac > 0.15:
            return {
                "decision": "APPROVE",
                "reason": "Low risk with acceptable returns",
                "auto_decidable": True,
            }
        elif pd_score > 0.15:
            return {
                "decision": "DECLINE",
                "reason": "High probability of default",
                "auto_decidable": True,
            }
        else:
            return {
                "decision": "REFER",
                "reason": "Manual review required",
                "auto_decidable": False,
            }

    def prepare_features(self, customer_data: dict, bureau_data: dict) -> dict:
        """Prepare features for model input."""
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

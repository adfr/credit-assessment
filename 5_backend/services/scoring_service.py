"""
Scoring Service
Handles PD/LGD scoring using either local models or CML endpoints.
"""

import os
import sys
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add endpoints to path for local imports
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
sys.path.insert(0, str(PROJECT_ROOT / "4_endpoints"))

# CML Model Endpoint Configuration
CML_MODEL_URL = os.environ.get(
    "CML_MODEL_URL",
    "https://modelservice.ml-40c12122-7f5.se-sandb.a465-9q4k.cloudera.site/model"
)
CML_PD_ACCESS_KEY = os.environ.get("CML_PD_ACCESS_KEY", "mzpyohap2x3r16t6pbe6mdiunw1xorzd")
CML_LGD_ACCESS_KEY = os.environ.get("CML_LGD_ACCESS_KEY", "mvpbjq5laskfzpti8sonbd4fi0heocx8")


class ScoringService:
    """
    Service for credit risk scoring.
    Supports both local model calls and CML endpoint calls.
    """

    def __init__(self):
        self.mode = os.environ.get("SCORING_MODE", "cml")  # cml or local
        self.cml_url = CML_MODEL_URL
        self.pd_access_key = CML_PD_ACCESS_KEY
        self.lgd_access_key = CML_LGD_ACCESS_KEY
        print(f"[SCORING_SERVICE] Initialized in {self.mode} mode")

    def _call_cml_endpoint(self, access_key: str, features: Dict[str, Any], model_name: str) -> Dict[str, Any]:
        """Call CML model endpoint."""
        payload = {
            "accessKey": access_key,
            "request": features
        }

        print(f"[SCORING_SERVICE] Calling CML {model_name} endpoint...")
        print(f"[SCORING_SERVICE] URL: {self.cml_url}")
        print(f"[SCORING_SERVICE] Features: {list(features.keys())}")

        try:
            response = requests.post(
                self.cml_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            print(f"[SCORING_SERVICE] CML {model_name} response: {result}")

            # CML returns response in 'response' key
            if "response" in result:
                return result["response"]
            return result

        except requests.exceptions.RequestException as e:
            print(f"[SCORING_SERVICE] CML {model_name} error: {e}")
            raise

    def predict_pd(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict Probability of Default.

        Args:
            features: Customer and loan features

        Returns:
            Dictionary with pd_score, risk_grade, decision
        """
        if self.mode == "cml":
            try:
                return self._call_cml_endpoint(self.pd_access_key, features, "PD")
            except Exception as e:
                print(f"[SCORING_SERVICE] CML PD failed, falling back to local: {e}")

        # Local prediction (fallback)
        return self._local_pd_prediction(features)

    def predict_lgd(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict Loss Given Default.

        Args:
            features: Collateral and loan features

        Returns:
            Dictionary with lgd_score, recovery_rate
        """
        if self.mode == "cml":
            try:
                return self._call_cml_endpoint(self.lgd_access_key, features, "LGD")
            except Exception as e:
                print(f"[SCORING_SERVICE] CML LGD failed, falling back to local: {e}")

        # Local prediction (fallback)
        return self._local_lgd_prediction(features)

    def score_application(
        self,
        customer_data: Dict[str, Any],
        loan_request: Dict[str, Any],
        bureau_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Complete application scoring with PD, LGD, and derived metrics.

        Args:
            customer_data: Customer financial information
            loan_request: Loan request details
            bureau_data: Optional bureau/credit data

        Returns:
            Complete risk assessment with scores and decision
        """
        bureau_data = bureau_data or {}

        # Prepare features for PD model
        pd_features = self._prepare_pd_features(customer_data, loan_request, bureau_data)
        pd_result = self.predict_pd(pd_features)

        # Prepare features for LGD model
        lgd_features = self._prepare_lgd_features(customer_data, loan_request)
        lgd_result = self.predict_lgd(lgd_features)

        # Extract scores
        pd_score = pd_result.get("pd_score", 0.05)
        lgd_score = lgd_result.get("lgd_score", 0.50)

        # Calculate derived metrics
        loan_amount = loan_request.get("requested_amount", 1000000)
        expected_loss = pd_score * lgd_score * loan_amount

        # Economic Capital (Basel-like)
        economic_capital = self._calculate_economic_capital(pd_score, loan_amount)

        # RORAC
        rorac = self._calculate_rorac(
            loan_amount=loan_amount,
            expected_loss=expected_loss,
            economic_capital=economic_capital,
            interest_rate=loan_request.get("proposed_interest_rate", 0.06),
        )

        # Risk grade
        risk_grade = pd_result.get("risk_grade") or self._get_risk_grade(pd_score)

        # Decision
        initial_decision, requires_review = self._make_decision(pd_score, rorac)

        return {
            "pd_score": round(pd_score, 6),
            "lgd_score": round(lgd_score, 6),
            "expected_loss": round(expected_loss, 2),
            "economic_capital": round(economic_capital, 2),
            "rorac": round(rorac, 4),
            "risk_grade": risk_grade,
            "initial_decision": initial_decision,
            "requires_review": requires_review,
            "pd_details": pd_result,
            "lgd_details": lgd_result,
            "scoring_mode": self.mode,
            "scored_at": datetime.now().isoformat(),
        }

    def _prepare_pd_features(
        self,
        customer_data: Dict,
        loan_request: Dict,
        bureau_data: Dict,
    ) -> Dict[str, Any]:
        """Prepare features for PD model."""
        total_liabilities = customer_data.get("total_liabilities") or 1
        total_assets = customer_data.get("total_assets") or 1
        equity = max(total_assets - total_liabilities, 1)
        annual_revenue = customer_data.get("annual_revenue") or 1
        loan_amount = loan_request.get("requested_amount") or 1000000

        return {
            "debt_to_equity": total_liabilities / equity,
            "debt_to_assets": total_liabilities / total_assets,
            "current_ratio": customer_data.get("current_ratio", 1.5),
            "quick_ratio": customer_data.get("quick_ratio", 1.2),
            "interest_coverage_ratio": customer_data.get("interest_coverage_ratio", 3.0),
            "return_on_assets": customer_data.get("return_on_assets", 0.05),
            "return_on_equity": customer_data.get("return_on_equity", 0.10),
            "profit_margin": customer_data.get("profit_margin", 0.08),
            "credit_score_normalized": bureau_data.get("credit_score", 70) / 100,
            "payment_index_trend": bureau_data.get("payment_index", 80) - 75,
            "utilization_rate": bureau_data.get("utilization_rate", 0.50),
            "derogatory_ratio": bureau_data.get("derogatory_count", 0) / 10,
            "avg_days_past_due": bureau_data.get("avg_days_past_due", 5),
            "max_days_past_due": bureau_data.get("max_days_past_due", 30),
            "dpd_volatility": bureau_data.get("dpd_volatility", 10),
            "count_30dpd": bureau_data.get("count_30dpd", 0),
            "count_60dpd": bureau_data.get("count_60dpd", 0),
            "count_90dpd": bureau_data.get("count_90dpd", 0),
            "payment_consistency_score": bureau_data.get("payment_consistency", 0.85),
            "loan_to_revenue_ratio": loan_amount / annual_revenue,
            "loan_to_assets_ratio": loan_amount / total_assets,
            "industry_default_rate": bureau_data.get("industry_default_rate", 0.04),
            "industry_risk_tier": bureau_data.get("industry_risk_tier", 3),
        }

    def _prepare_lgd_features(
        self,
        customer_data: Dict,
        loan_request: Dict,
    ) -> Dict[str, Any]:
        """Prepare features for LGD model."""
        total_liabilities = customer_data.get("total_liabilities") or 1
        total_assets = customer_data.get("total_assets") or 1
        equity = max(total_assets - total_liabilities, 1)
        annual_revenue = customer_data.get("annual_revenue") or 1
        loan_amount = loan_request.get("requested_amount") or 1000000

        return {
            "collateral_type": loan_request.get("collateral_type", "unsecured"),
            "ltv_ratio": loan_request.get("ltv_ratio", 0.8),
            "loan_amount": loan_amount,
            "debt_to_equity": total_liabilities / equity,
            "current_ratio": customer_data.get("current_ratio", 1.5),
            "interest_coverage_ratio": customer_data.get("interest_coverage_ratio", 3.0),
            "credit_score_normalized": customer_data.get("credit_score", 70) / 100,
            "utilization_rate": customer_data.get("utilization_rate", 0.50),
            "loan_to_revenue_ratio": loan_amount / annual_revenue,
            "loan_to_assets_ratio": loan_amount / total_assets,
            "term_months": loan_request.get("term_months", 36),
            "interest_rate": loan_request.get("proposed_interest_rate", 0.06),
            "industry_risk_tier": customer_data.get("industry_risk_tier", 3),
        }

    def _calculate_economic_capital(self, pd_score: float, loan_amount: float) -> float:
        """Calculate economic capital using Basel-like risk weights."""
        if pd_score < 0.01:
            risk_weight = 0.20
        elif pd_score < 0.03:
            risk_weight = 0.50
        elif pd_score < 0.05:
            risk_weight = 0.75
        elif pd_score < 0.10:
            risk_weight = 1.00
        else:
            risk_weight = 1.50

        return loan_amount * risk_weight * 0.08

    def _calculate_rorac(
        self,
        loan_amount: float,
        expected_loss: float,
        economic_capital: float,
        interest_rate: float,
    ) -> float:
        """Calculate Risk-Adjusted Return on Capital."""
        funding_cost = 0.02
        operating_cost_rate = 0.01

        net_interest = loan_amount * (interest_rate - funding_cost)
        operating_costs = loan_amount * operating_cost_rate
        net_profit = net_interest - expected_loss - operating_costs

        return net_profit / max(economic_capital, 1)

    def _get_risk_grade(self, pd_score: float) -> str:
        """Convert PD to risk grade."""
        if pd_score < 0.01:
            return "A"
        elif pd_score < 0.03:
            return "BBB"
        elif pd_score < 0.05:
            return "BB"
        elif pd_score < 0.10:
            return "B"
        else:
            return "CCC"

    def _make_decision(self, pd_score: float, rorac: float) -> tuple:
        """Make initial decision based on scores."""
        if pd_score < 0.03 and rorac > 0.12:
            return "APPROVE", False
        elif pd_score > 0.15:
            return "DECLINE", False
        else:
            return "REFER", True

    def _local_pd_prediction(self, features: Dict) -> Dict:
        """Local PD prediction using trained model or heuristics."""
        try:
            from cml_serve_pd import predict
            return predict(features)
        except Exception as e:
            # Fallback to simple heuristics
            debt_to_equity = features.get("debt_to_equity", 1.5)
            credit_score = features.get("credit_score_normalized", 0.70)

            base_pd = 0.03
            if debt_to_equity > 2:
                base_pd += 0.02
            if credit_score < 0.60:
                base_pd += 0.03

            pd_score = min(base_pd, 0.50)

            return {
                "status": "success",
                "pd_score": pd_score,
                "risk_grade": self._get_risk_grade(pd_score),
                "source": "heuristic",
            }

    def _local_lgd_prediction(self, features: Dict) -> Dict:
        """Local LGD prediction using trained model or assumptions."""
        try:
            from cml_serve_lgd import predict
            return predict(features)
        except Exception as e:
            # Fallback to collateral-based assumptions
            collateral_map = {
                "real_estate": 0.35,
                "equipment": 0.45,
                "unsecured": 0.75,
            }
            collateral_type = features.get("collateral_type", "unsecured")
            lgd_score = collateral_map.get(collateral_type, 0.55)

            return {
                "status": "success",
                "lgd_score": lgd_score,
                "source": "assumption",
            }


# Singleton instance
_scoring_service: Optional[ScoringService] = None


def get_scoring_service() -> ScoringService:
    """Get or create singleton scoring service."""
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = ScoringService()
    return _scoring_service

#!/usr/bin/env python3
"""
CML Model Client
Unified client for calling PD and LGD models deployed on Cloudera ML.
Supports both local development (direct calls) and production (CML API).
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class DeploymentMode(Enum):
    LOCAL = "local"
    CML = "cml"


@dataclass
class CMLConfig:
    """CML deployment configuration."""
    # CML API settings
    cml_api_url: str = ""
    cml_api_key: str = ""

    # Model endpoints
    pd_model_endpoint: str = ""
    lgd_model_endpoint: str = ""

    # Deployment mode
    mode: DeploymentMode = DeploymentMode.LOCAL

    # Timeouts
    request_timeout: int = 30

    @classmethod
    def from_env(cls) -> "CMLConfig":
        """Load configuration from environment variables."""
        mode_str = os.environ.get("CML_DEPLOYMENT_MODE", "local").lower()
        mode = DeploymentMode.CML if mode_str == "cml" else DeploymentMode.LOCAL

        return cls(
            cml_api_url=os.environ.get("CML_API_URL", ""),
            cml_api_key=os.environ.get("CML_API_KEY", ""),
            pd_model_endpoint=os.environ.get("CML_PD_MODEL_ENDPOINT", ""),
            lgd_model_endpoint=os.environ.get("CML_LGD_MODEL_ENDPOINT", ""),
            mode=mode,
            request_timeout=int(os.environ.get("CML_REQUEST_TIMEOUT", "30")),
        )


class CMLModelClient:
    """
    Client for calling CML-deployed models.

    Usage:
        # Local development (direct function calls)
        client = CMLModelClient()
        pd_result = client.predict_pd(features)

        # Production (CML API calls)
        config = CMLConfig.from_env()
        client = CMLModelClient(config)
        pd_result = client.predict_pd(features)
    """

    def __init__(self, config: Optional[CMLConfig] = None):
        self.config = config or CMLConfig.from_env()
        self._session: Optional[requests.Session] = None

        # Local model imports (lazy loaded)
        self._pd_predict = None
        self._lgd_predict = None

    @property
    def session(self) -> requests.Session:
        """Get or create requests session."""
        if self._session is None:
            self._session = requests.Session()
            if self.config.cml_api_key:
                self._session.headers.update({
                    "Authorization": f"Bearer {self.config.cml_api_key}",
                    "Content-Type": "application/json",
                })
        return self._session

    def _call_cml_endpoint(self, endpoint: str, payload: Dict) -> Dict:
        """Call a CML model endpoint."""
        try:
            response = self.session.post(
                endpoint,
                json={"request": payload},
                timeout=self.config.request_timeout,
            )
            response.raise_for_status()
            result = response.json()

            # CML wraps response in "response" key
            if "response" in result:
                return result["response"]
            return result

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error_type": "cml_api_error",
                "error": str(e),
            }

    def _load_local_pd(self):
        """Lazy load local PD model."""
        if self._pd_predict is None:
            from cml_serve_pd import predict
            self._pd_predict = predict
        return self._pd_predict

    def _load_local_lgd(self):
        """Lazy load local LGD model."""
        if self._lgd_predict is None:
            from cml_serve_lgd import predict
            self._lgd_predict = predict
        return self._lgd_predict

    def predict_pd(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict Probability of Default.

        Args:
            features: Dictionary of customer/loan features

        Returns:
            Dictionary with pd_score, risk_grade, decision, etc.
        """
        if self.config.mode == DeploymentMode.CML:
            if not self.config.pd_model_endpoint:
                return {
                    "status": "error",
                    "error": "PD model endpoint not configured",
                }
            return self._call_cml_endpoint(
                self.config.pd_model_endpoint,
                features,
            )
        else:
            # Local mode - direct function call
            predict_fn = self._load_local_pd()
            return predict_fn(features)

    def predict_lgd(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict Loss Given Default.

        Args:
            features: Dictionary of collateral/loan features

        Returns:
            Dictionary with lgd_score, recovery_rate, etc.
        """
        if self.config.mode == DeploymentMode.CML:
            if not self.config.lgd_model_endpoint:
                return {
                    "status": "error",
                    "error": "LGD model endpoint not configured",
                }
            return self._call_cml_endpoint(
                self.config.lgd_model_endpoint,
                features,
            )
        else:
            # Local mode - direct function call
            predict_fn = self._load_local_lgd()
            return predict_fn(features)

    def predict_risk(
        self,
        customer_features: Dict[str, Any],
        loan_features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Combined risk prediction (PD + LGD + Expected Loss).

        Args:
            customer_features: Customer financial data
            loan_features: Loan request data

        Returns:
            Combined risk assessment with EL calculation
        """
        # Merge features for PD
        pd_features = {**customer_features, **loan_features}
        pd_result = self.predict_pd(pd_features)

        # LGD features
        lgd_features = {
            "collateral_type": loan_features.get("collateral_type", "unsecured"),
            "ltv_ratio": loan_features.get("ltv_ratio"),
            "loan_amount": loan_features.get("requested_amount"),
            **customer_features,
        }
        lgd_result = self.predict_lgd(lgd_features)

        # Calculate Expected Loss if both succeeded
        if pd_result.get("status") == "success" and lgd_result.get("status") == "success":
            pd_score = pd_result["pd_score"]
            lgd_score = lgd_result["lgd_score"]
            loan_amount = loan_features.get("requested_amount", 0)

            expected_loss = pd_score * lgd_score * loan_amount

            # Calculate economic capital (Basel-like)
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

            economic_capital = loan_amount * risk_weight * 0.08

            # RORAC calculation
            interest_rate = loan_features.get("proposed_interest_rate", 0.06)
            funding_cost = 0.02
            operating_cost_rate = 0.01

            net_interest = loan_amount * (interest_rate - funding_cost)
            operating_costs = loan_amount * operating_cost_rate
            net_profit = net_interest - expected_loss - operating_costs
            rorac = net_profit / max(economic_capital, 1)

            return {
                "status": "success",
                "pd": pd_result,
                "lgd": lgd_result,
                "expected_loss": round(expected_loss, 2),
                "economic_capital": round(economic_capital, 2),
                "rorac": round(rorac, 4),
                "risk_grade": pd_result.get("risk_grade"),
                "decision": pd_result.get("decision"),
            }

        return {
            "status": "error",
            "pd": pd_result,
            "lgd": lgd_result,
            "error": "One or more model predictions failed",
        }

    def health_check(self) -> Dict[str, Any]:
        """Check health of all model endpoints."""
        results = {
            "mode": self.config.mode.value,
            "pd_model": None,
            "lgd_model": None,
        }

        if self.config.mode == DeploymentMode.CML:
            # Check CML endpoints
            if self.config.pd_model_endpoint:
                try:
                    # Simple test call
                    response = self.session.get(
                        self.config.pd_model_endpoint.replace("/predict", "/health"),
                        timeout=10,
                    )
                    results["pd_model"] = {
                        "status": "healthy" if response.ok else "unhealthy",
                        "endpoint": self.config.pd_model_endpoint,
                    }
                except Exception as e:
                    results["pd_model"] = {"status": "error", "error": str(e)}

            if self.config.lgd_model_endpoint:
                try:
                    response = self.session.get(
                        self.config.lgd_model_endpoint.replace("/predict", "/health"),
                        timeout=10,
                    )
                    results["lgd_model"] = {
                        "status": "healthy" if response.ok else "unhealthy",
                        "endpoint": self.config.lgd_model_endpoint,
                    }
                except Exception as e:
                    results["lgd_model"] = {"status": "error", "error": str(e)}
        else:
            # Local mode - check model loading
            try:
                from cml_serve_pd import health_check as pd_health
                results["pd_model"] = pd_health()
            except Exception as e:
                results["pd_model"] = {"status": "error", "error": str(e)}

            try:
                from cml_serve_lgd import health_check as lgd_health
                results["lgd_model"] = lgd_health()
            except Exception as e:
                results["lgd_model"] = {"status": "error", "error": str(e)}

        return results


# Singleton instance for easy import
_client: Optional[CMLModelClient] = None


def get_client() -> CMLModelClient:
    """Get or create the singleton CML client."""
    global _client
    if _client is None:
        _client = CMLModelClient()
    return _client


# =============================================================================
# Local Testing
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CML Model Client - Test")
    print("=" * 60)

    client = CMLModelClient()

    # Health check
    print("\n[Health Check]")
    health = client.health_check()
    print(json.dumps(health, indent=2, default=str))

    # Test combined prediction
    print("\n[Combined Risk Prediction]")
    customer = {
        "debt_to_equity": 1.5,
        "debt_to_assets": 0.6,
        "current_ratio": 1.8,
        "interest_coverage_ratio": 4.5,
        "credit_score_normalized": 0.75,
        "utilization_rate": 0.4,
        "industry_risk_tier": 3,
    }

    loan = {
        "requested_amount": 1000000,
        "collateral_type": "equipment",
        "ltv_ratio": 0.7,
        "proposed_interest_rate": 0.065,
    }

    result = client.predict_risk(customer, loan)
    print(json.dumps(result, indent=2, default=str))

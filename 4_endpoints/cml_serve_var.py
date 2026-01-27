#!/usr/bin/env python3
"""
CML Model Endpoint for VaR (Value at Risk)
Ready for deployment as Cloudera ML Model Endpoint.

Deployment:
1. Create a new Model in CML
2. Set this file as the entry point
3. Set function name: predict
4. Configure resources (CPU/Memory)
5. Deploy
"""

import os
import math
import json
from typing import Dict, Any, Optional
from datetime import datetime

import numpy as np
from scipy import stats

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

MODEL_NAME = "var_model"
MODEL_VERSION = os.environ.get("MODEL_VERSION", "1.0")
DEFAULT_SIMULATIONS = int(os.environ.get("VAR_DEFAULT_SIMULATIONS", "100000"))
DEFAULT_CONFIDENCE = float(os.environ.get("VAR_DEFAULT_CONFIDENCE", "0.999"))
DEFAULT_CORRELATION = float(os.environ.get("VAR_DEFAULT_CORRELATION", "0.2"))


# =============================================================================
# VaR Calculation Engine
# =============================================================================

def calculate_var_monte_carlo(
    exposure: float,
    pd: float,
    lgd: float,
    confidence: float = 0.999,
    simulations: int = 100000,
    correlation: float = 0.2,
    seed: Optional[int] = 42
) -> Dict[str, Any]:
    """
    Calculate Value at Risk (VaR) using Monte Carlo simulation.

    Implements a single-factor Gaussian copula model for credit risk:
    - Z = sqrt(rho) * M + sqrt(1-rho) * epsilon
    - Where M is systematic factor, epsilon is idiosyncratic

    Args:
        exposure: Exposure at Default
        pd: Probability of Default (decimal)
        lgd: Loss Given Default (decimal)
        confidence: Confidence level (e.g., 0.999 for 99.9%)
        simulations: Number of Monte Carlo simulations
        correlation: Asset correlation for systematic risk factor
        seed: Random seed for reproducibility

    Returns:
        dict with VaR metrics
    """
    if seed is not None:
        np.random.seed(seed)

    # Constrain PD to valid range
    pd = max(0.0003, min(pd, 0.9999))

    # Default threshold (inverse normal of PD)
    threshold = stats.norm.ppf(pd)

    # Vectorized Monte Carlo simulation
    # Systematic risk factor (market-wide shock)
    systematic = np.random.standard_normal(simulations)

    # Idiosyncratic factor (borrower-specific)
    idiosyncratic = np.random.standard_normal(simulations)

    # Combined factor using single-factor model
    z = math.sqrt(correlation) * systematic + math.sqrt(1 - correlation) * idiosyncratic

    # Default indicator and losses
    defaults = z < threshold
    losses = np.where(defaults, exposure * lgd, 0.0)

    # Calculate VaR at different confidence levels
    var_999 = np.percentile(losses, 99.9)
    var_99 = np.percentile(losses, 99)
    var_95 = np.percentile(losses, 95)
    var_custom = np.percentile(losses, confidence * 100)

    # Expected loss (mean)
    expected_loss = np.mean(losses)

    # Standard deviation of losses
    loss_std = np.std(losses)

    # Expected Shortfall (CVaR) - average loss beyond VaR
    tail_mask = losses >= var_custom
    tail_losses = losses[tail_mask]
    expected_shortfall = np.mean(tail_losses) if len(tail_losses) > 0 else var_custom

    # Simulated default rate
    simulated_default_rate = np.mean(defaults)

    return {
        "var": float(var_custom),
        "var_999": float(var_999),
        "var_99": float(var_99),
        "var_95": float(var_95),
        "expected_loss": float(expected_loss),
        "expected_shortfall": float(expected_shortfall),
        "loss_std": float(loss_std),
        "simulated_default_rate": float(simulated_default_rate),
        "confidence": confidence,
        "simulations": simulations,
        "correlation": correlation,
    }


def calculate_var_analytical(
    exposure: float,
    pd: float,
    lgd: float,
    confidence: float = 0.999,
    correlation: float = 0.2
) -> Dict[str, Any]:
    """
    Calculate VaR using analytical Vasicek formula.

    This provides a closed-form solution for comparison with Monte Carlo.
    """
    # Constrain PD
    pd = max(0.0003, min(pd, 0.9999))

    # Expected loss
    el = exposure * pd * lgd

    # Analytical VaR using Vasicek single-factor model
    norm_pd = stats.norm.ppf(pd)
    norm_conf = stats.norm.ppf(confidence)

    # Conditional default probability at confidence level
    conditional_pd = stats.norm.cdf(
        (norm_pd + math.sqrt(correlation) * norm_conf) /
        math.sqrt(1 - correlation)
    )

    # VaR
    var_analytical = exposure * conditional_pd * lgd

    return {
        "var_analytical": float(var_analytical),
        "expected_loss": float(el),
        "conditional_pd": float(conditional_pd),
        "unexpected_loss": float(var_analytical - el),
    }


# =============================================================================
# CML Model Endpoint
# =============================================================================

@models.cml_model
def predict(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    CML Model Endpoint for VaR calculation.

    Input Schema:
    {
        "exposure": float,      # Exposure at Default (required)
        "pd": float,            # Probability of Default, 0-1 (required)
        "lgd": float,           # Loss Given Default, 0-1 (required)
        "confidence": float,    # Confidence level (default: 0.999)
        "simulations": int,     # Number of MC simulations (default: 100000)
        "correlation": float,   # Asset correlation (default: 0.2)
        "include_analytical": bool  # Include analytical VaR (default: false)
    }

    Output Schema:
    {
        "status": "success" | "error",
        "var": float,           # VaR at specified confidence
        "var_99": float,        # VaR at 99%
        "var_95": float,        # VaR at 95%
        "expected_loss": float,
        "expected_shortfall": float,  # CVaR
        "model_version": str,
        "timestamp": str
    }
    """
    timestamp = datetime.now().isoformat()

    try:
        # Extract and validate required parameters
        exposure = args.get("exposure")
        pd = args.get("pd")
        lgd = args.get("lgd")

        # Validation
        errors = []
        if exposure is None:
            errors.append("exposure is required")
        elif float(exposure) <= 0:
            errors.append("exposure must be positive")

        if pd is None:
            errors.append("pd is required")
        elif not (0 < float(pd) < 1):
            errors.append("pd must be between 0 and 1")

        if lgd is None:
            errors.append("lgd is required")
        elif not (0 < float(lgd) <= 1):
            errors.append("lgd must be between 0 and 1")

        if errors:
            return {
                "status": "error",
                "error_type": "validation_error",
                "errors": errors,
                "var": None,
                "timestamp": timestamp,
            }

        # Convert to floats
        exposure = float(exposure)
        pd = float(pd)
        lgd = float(lgd)

        # Extract optional parameters with defaults
        confidence = float(args.get("confidence", DEFAULT_CONFIDENCE))
        simulations = int(args.get("simulations", DEFAULT_SIMULATIONS))
        correlation = float(args.get("correlation", DEFAULT_CORRELATION))
        include_analytical = args.get("include_analytical", False)

        # Calculate VaR using Monte Carlo
        mc_result = calculate_var_monte_carlo(
            exposure=exposure,
            pd=pd,
            lgd=lgd,
            confidence=confidence,
            simulations=simulations,
            correlation=correlation,
        )

        # Build response
        response = {
            "status": "success",
            "var": round(mc_result["var"], 2),
            "var_999": round(mc_result["var_999"], 2),
            "var_99": round(mc_result["var_99"], 2),
            "var_95": round(mc_result["var_95"], 2),
            "expected_loss": round(mc_result["expected_loss"], 2),
            "expected_shortfall": round(mc_result["expected_shortfall"], 2),
            "loss_std": round(mc_result["loss_std"], 2),
            "simulated_default_rate": round(mc_result["simulated_default_rate"], 6),
            "confidence": confidence,
            "simulations": simulations,
            "correlation": correlation,
            "exposure": exposure,
            "pd": pd,
            "lgd": lgd,
            "model_version": MODEL_VERSION,
            "methodology": "Monte_Carlo_Single_Factor",
            "timestamp": timestamp,
        }

        # Optionally include analytical comparison
        if include_analytical:
            analytical = calculate_var_analytical(
                exposure=exposure,
                pd=pd,
                lgd=lgd,
                confidence=confidence,
                correlation=correlation,
            )
            response["var_analytical"] = round(analytical["var_analytical"], 2)
            response["analytical_vs_mc_diff"] = round(
                analytical["var_analytical"] - mc_result["var"], 2
            )

        return response

    except ValueError as e:
        return {
            "status": "error",
            "error_type": "value_error",
            "error": str(e),
            "var": None,
            "timestamp": timestamp,
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "calculation_error",
            "error": str(e),
            "var": None,
            "timestamp": timestamp,
        }


def health_check() -> Dict[str, Any]:
    """Health check endpoint for CML model monitoring."""
    try:
        # Run a simple calculation to verify functionality
        test_result = calculate_var_monte_carlo(
            exposure=1000000,
            pd=0.05,
            lgd=0.45,
            simulations=1000,  # Reduced for health check
        )

        return {
            "status": "healthy",
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "methodology": "Monte_Carlo_Single_Factor",
            "default_simulations": DEFAULT_SIMULATIONS,
            "default_confidence": DEFAULT_CONFIDENCE,
            "default_correlation": DEFAULT_CORRELATION,
            "test_var": round(test_result["var"], 2),
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
    print("VaR Model Endpoint - Local Test")
    print("=" * 60)

    # Health check
    print("\n[Health Check]")
    health = health_check()
    print(json.dumps(health, indent=2, default=str))

    # Test prediction
    test_inputs = [
        {
            "exposure": 1000000,
            "pd": 0.05,
            "lgd": 0.45,
            "confidence": 0.999,
            "simulations": 100000,
            "correlation": 0.2,
            "include_analytical": True,
        },
        {
            "exposure": 5000000,
            "pd": 0.02,
            "lgd": 0.35,
            "confidence": 0.99,
        },
    ]

    for i, test_input in enumerate(test_inputs, 1):
        print(f"\n[Prediction Test {i}]")
        print(f"Input: {json.dumps(test_input, indent=2)}")

        result = predict(test_input)
        print(f"Result: {json.dumps(result, indent=2, default=str)}")

#!/usr/bin/env python3
"""
CML Model Endpoint for Regulatory Capital (Basel IRB)
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

MODEL_NAME = "regulatory_capital_model"
MODEL_VERSION = os.environ.get("MODEL_VERSION", "1.0")
DEFAULT_MATURITY = float(os.environ.get("RC_DEFAULT_MATURITY", "2.5"))
CONFIDENCE_LEVEL = 0.999  # Basel IRB uses 99.9% confidence


# =============================================================================
# Regulatory Capital Calculation Engine
# =============================================================================

def calculate_asset_correlation(pd: float, asset_class: str = "corporate") -> float:
    """
    Calculate asset correlation using Basel formula.

    Args:
        pd: Probability of Default
        asset_class: Asset class (corporate, sme, retail_mortgage, retail_other)

    Returns:
        Asset correlation value
    """
    if asset_class == "corporate":
        # Corporate exposure correlation formula
        r = 0.12 * (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)) + \
            0.24 * (1 - (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)))
    elif asset_class == "sme":
        # SME correlation with size adjustment (assuming mid-size)
        r_base = 0.12 * (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)) + \
                 0.24 * (1 - (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)))
        # Size adjustment for SME (assuming 20M revenue)
        size_adj = 0.04 * (1 - (min(50, max(5, 20)) - 5) / 45)
        r = r_base - size_adj
    elif asset_class == "retail_mortgage":
        r = 0.15  # Fixed correlation for residential mortgages
    elif asset_class == "retail_other":
        r = 0.04  # Fixed correlation for other retail
    else:
        # Default to corporate
        r = 0.12 * (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)) + \
            0.24 * (1 - (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)))

    return r


def calculate_maturity_adjustment(pd: float, maturity: float) -> float:
    """
    Calculate maturity adjustment factor.

    Args:
        pd: Probability of Default
        maturity: Effective maturity in years

    Returns:
        Maturity adjustment factor
    """
    b = (0.11852 - 0.05478 * math.log(pd)) ** 2
    maturity_adj = (1 + (maturity - 2.5) * b) / (1 - 1.5 * b)
    return maturity_adj


def calculate_regulatory_capital(
    exposure: float,
    pd: float,
    lgd: float,
    maturity: float = 2.5,
    correlation: Optional[float] = None,
    asset_class: str = "corporate"
) -> Dict[str, Any]:
    """
    Calculate Basel IRB Regulatory Capital.

    Implements the Basel II/III Internal Ratings-Based (IRB) approach
    for calculating regulatory capital requirements.

    Args:
        exposure: Exposure at Default (EAD)
        pd: Probability of Default (decimal, e.g., 0.05 for 5%)
        lgd: Loss Given Default (decimal, e.g., 0.45 for 45%)
        maturity: Effective maturity in years (1-5, default 2.5)
        correlation: Asset correlation (if None, uses Basel formula)
        asset_class: Asset class for correlation calculation

    Returns:
        dict with regulatory capital breakdown
    """
    # Constrain PD to Basel floor/ceiling
    pd = max(0.0003, min(pd, 0.9999))

    # Constrain maturity
    maturity = max(1.0, min(maturity, 5.0))

    # Asset correlation
    if correlation is None:
        correlation = calculate_asset_correlation(pd, asset_class)

    # Maturity adjustment (only for non-retail)
    if asset_class in ["corporate", "sme"]:
        maturity_adj = calculate_maturity_adjustment(pd, maturity)
    else:
        maturity_adj = 1.0  # No maturity adjustment for retail

    # Capital requirement (K) using Vasicek formula
    norm_pd = stats.norm.ppf(pd)
    norm_999 = stats.norm.ppf(CONFIDENCE_LEVEL)

    # Conditional probability of default at 99.9% confidence
    conditional_pd = stats.norm.cdf(
        (norm_pd + math.sqrt(correlation) * norm_999) /
        math.sqrt(1 - correlation)
    )

    # Capital requirement before maturity adjustment
    k_base = lgd * conditional_pd - pd * lgd

    # Apply maturity adjustment
    k = k_base * maturity_adj

    # Risk-weighted assets (RWA = K * 12.5 * EAD)
    rwa = k * 12.5 * exposure

    # Minimum capital requirement (8% of RWA)
    capital = rwa * 0.08

    # Expected loss
    el = exposure * pd * lgd

    # Unexpected loss (difference between stressed and expected)
    ul = exposure * conditional_pd * lgd - el

    return {
        "regulatory_capital": capital,
        "risk_weighted_assets": rwa,
        "capital_requirement_k": k,
        "k_before_maturity_adj": k_base,
        "expected_loss": el,
        "unexpected_loss": ul,
        "asset_correlation": correlation,
        "maturity_adjustment": maturity_adj,
        "conditional_pd": conditional_pd,
        "exposure": exposure,
        "pd": pd,
        "lgd": lgd,
        "maturity": maturity,
        "asset_class": asset_class,
    }


def get_capital_adequacy_tier(capital_ratio: float) -> Dict[str, Any]:
    """
    Determine capital adequacy tier based on capital ratio.

    Args:
        capital_ratio: Regulatory capital / Exposure

    Returns:
        dict with tier information
    """
    if capital_ratio >= 0.105:
        tier = "WELL_CAPITALIZED"
        description = "Exceeds all regulatory minimums with buffer"
        action = "None required"
    elif capital_ratio >= 0.08:
        tier = "ADEQUATELY_CAPITALIZED"
        description = "Meets minimum regulatory requirements"
        action = "Monitor closely"
    elif capital_ratio >= 0.06:
        tier = "UNDERCAPITALIZED"
        description = "Below minimum requirements"
        action = "Capital restoration plan required"
    elif capital_ratio >= 0.04:
        tier = "SIGNIFICANTLY_UNDERCAPITALIZED"
        description = "Significantly below requirements"
        action = "Immediate corrective action required"
    else:
        tier = "CRITICALLY_UNDERCAPITALIZED"
        description = "Critically low capital"
        action = "Resolution or receivership"

    return {
        "tier": tier,
        "description": description,
        "recommended_action": action,
    }


# =============================================================================
# CML Model Endpoint
# =============================================================================

@models.cml_model
def predict(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    CML Model Endpoint for Regulatory Capital calculation.

    Input Schema:
    {
        "exposure": float,      # Exposure at Default (required)
        "pd": float,            # Probability of Default, 0-1 (required)
        "lgd": float,           # Loss Given Default, 0-1 (required)
        "maturity": float,      # Effective maturity in years (default: 2.5)
        "correlation": float,   # Asset correlation (default: Basel formula)
        "asset_class": str      # corporate, sme, retail_mortgage, retail_other
    }

    Output Schema:
    {
        "status": "success" | "error",
        "regulatory_capital": float,
        "risk_weighted_assets": float,
        "capital_requirement_k": float,
        "expected_loss": float,
        "capital_ratio": float,
        "capital_tier": str,
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
                "regulatory_capital": None,
                "timestamp": timestamp,
            }

        # Convert to floats
        exposure = float(exposure)
        pd = float(pd)
        lgd = float(lgd)

        # Extract optional parameters
        maturity = float(args.get("maturity", DEFAULT_MATURITY))
        correlation = args.get("correlation")
        if correlation is not None:
            correlation = float(correlation)
        asset_class = args.get("asset_class", "corporate")

        # Validate asset class
        valid_asset_classes = ["corporate", "sme", "retail_mortgage", "retail_other"]
        if asset_class not in valid_asset_classes:
            asset_class = "corporate"

        # Calculate regulatory capital
        result = calculate_regulatory_capital(
            exposure=exposure,
            pd=pd,
            lgd=lgd,
            maturity=maturity,
            correlation=correlation,
            asset_class=asset_class,
        )

        # Calculate capital ratio and tier
        capital_ratio = result["regulatory_capital"] / exposure if exposure > 0 else 0
        tier_info = get_capital_adequacy_tier(capital_ratio)

        # Build response
        return {
            "status": "success",
            "regulatory_capital": round(result["regulatory_capital"], 2),
            "risk_weighted_assets": round(result["risk_weighted_assets"], 2),
            "capital_requirement_k": round(result["capital_requirement_k"], 6),
            "k_before_maturity_adj": round(result["k_before_maturity_adj"], 6),
            "expected_loss": round(result["expected_loss"], 2),
            "unexpected_loss": round(result["unexpected_loss"], 2),
            "asset_correlation": round(result["asset_correlation"], 6),
            "maturity_adjustment": round(result["maturity_adjustment"], 6),
            "conditional_pd": round(result["conditional_pd"], 6),
            "capital_ratio": round(capital_ratio, 6),
            "capital_tier": tier_info["tier"],
            "tier_description": tier_info["description"],
            "recommended_action": tier_info["recommended_action"],
            "exposure": exposure,
            "pd": pd,
            "lgd": lgd,
            "maturity": maturity,
            "asset_class": asset_class,
            "model_version": MODEL_VERSION,
            "methodology": "Basel_IRB_Advanced",
            "confidence_level": CONFIDENCE_LEVEL,
            "timestamp": timestamp,
        }

    except ValueError as e:
        return {
            "status": "error",
            "error_type": "value_error",
            "error": str(e),
            "regulatory_capital": None,
            "timestamp": timestamp,
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "calculation_error",
            "error": str(e),
            "regulatory_capital": None,
            "timestamp": timestamp,
        }


def health_check() -> Dict[str, Any]:
    """Health check endpoint for CML model monitoring."""
    try:
        # Run a simple calculation to verify functionality
        test_result = calculate_regulatory_capital(
            exposure=1000000,
            pd=0.05,
            lgd=0.45,
        )

        return {
            "status": "healthy",
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "methodology": "Basel_IRB_Advanced",
            "confidence_level": CONFIDENCE_LEVEL,
            "default_maturity": DEFAULT_MATURITY,
            "test_capital": round(test_result["regulatory_capital"], 2),
            "test_rwa": round(test_result["risk_weighted_assets"], 2),
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
    print("Regulatory Capital Model Endpoint - Local Test")
    print("=" * 60)

    # Health check
    print("\n[Health Check]")
    health = health_check()
    print(json.dumps(health, indent=2, default=str))

    # Test predictions for different asset classes
    test_inputs = [
        {
            "exposure": 1000000,
            "pd": 0.05,
            "lgd": 0.45,
            "maturity": 3.0,
            "asset_class": "corporate",
        },
        {
            "exposure": 500000,
            "pd": 0.03,
            "lgd": 0.40,
            "maturity": 2.0,
            "asset_class": "sme",
        },
        {
            "exposure": 250000,
            "pd": 0.02,
            "lgd": 0.20,
            "asset_class": "retail_mortgage",
        },
    ]

    for i, test_input in enumerate(test_inputs, 1):
        print(f"\n[Prediction Test {i} - {test_input.get('asset_class', 'corporate')}]")
        print(f"Input: {json.dumps(test_input, indent=2)}")

        result = predict(test_input)
        print(f"Result: {json.dumps(result, indent=2, default=str)}")

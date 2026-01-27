#!/usr/bin/env python3
"""
CML Model Endpoint for Regulatory Capital (Basel IRB)
Serves Basel II/III IRB capital calculations for real-time risk assessment.
"""

import math
from typing import Optional
from datetime import datetime

from scipy import stats


def calculate_regulatory_capital(
    exposure: float,
    pd: float,
    lgd: float,
    maturity: float = 2.5,
    correlation: Optional[float] = None
) -> dict:
    """
    Calculate Basel IRB Regulatory Capital.

    Uses the Basel II/III IRB formula for corporate exposures.

    Args:
        exposure: Exposure at Default
        pd: Probability of Default (decimal)
        lgd: Loss Given Default (decimal)
        maturity: Effective maturity in years
        correlation: Asset correlation (if None, uses Basel formula)

    Returns:
        dict with capital calculation breakdown
    """
    # Constrain PD
    pd = max(0.0003, min(pd, 0.9999))

    # Asset correlation (Basel formula for corporates)
    if correlation is None:
        correlation = 0.12 * (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)) + \
                      0.24 * (1 - (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)))

    # Maturity adjustment
    b = (0.11852 - 0.05478 * math.log(pd)) ** 2
    maturity_adj = (1 + (maturity - 2.5) * b) / (1 - 1.5 * b)

    # Capital requirement (K)
    norm_pd = stats.norm.ppf(pd)
    norm_999 = stats.norm.ppf(0.999)

    conditional_pd = stats.norm.cdf(
        (norm_pd + math.sqrt(correlation) * norm_999) /
        math.sqrt(1 - correlation)
    )

    k = (lgd * conditional_pd - pd * lgd) * maturity_adj

    # Risk-weighted assets
    rwa = k * 12.5 * exposure

    # Capital requirement (8% of RWA)
    capital = rwa * 0.08

    # Expected loss
    el = exposure * pd * lgd

    return {
        "regulatory_capital": capital,
        "risk_weighted_assets": rwa,
        "capital_requirement_k": k,
        "asset_correlation": correlation,
        "maturity_adjustment": maturity_adj,
        "conditional_pd": conditional_pd,
        "expected_loss": el,
        "exposure": exposure,
        "pd": pd,
        "lgd": lgd,
        "maturity": maturity,
    }


def get_capital_tier(capital_ratio: float) -> str:
    """Get capital adequacy tier based on capital ratio."""
    if capital_ratio >= 0.15:
        return "WELL_CAPITALIZED"
    elif capital_ratio >= 0.10:
        return "ADEQUATELY_CAPITALIZED"
    elif capital_ratio >= 0.08:
        return "UNDERCAPITALIZED"
    elif capital_ratio >= 0.06:
        return "SIGNIFICANTLY_UNDERCAPITALIZED"
    else:
        return "CRITICALLY_UNDERCAPITALIZED"


def predict(args: dict) -> dict:
    """
    Main prediction function for CML endpoint.

    Args:
        args: Dictionary containing:
            - exposure: Exposure at Default (required)
            - pd: Probability of Default as decimal (required)
            - lgd: Loss Given Default as decimal (required)
            - maturity: Effective maturity in years (default: 2.5)
            - correlation: Asset correlation (default: Basel formula)

    Returns:
        Dictionary with regulatory capital calculation results
    """
    timestamp = datetime.now().isoformat()

    try:
        # Extract required parameters
        exposure = float(args.get("exposure", 0))
        pd = float(args.get("pd", 0))
        lgd = float(args.get("lgd", 0))

        # Validate required parameters
        if exposure <= 0:
            return {
                "status": "error",
                "error": "exposure must be positive",
                "timestamp": timestamp,
            }
        if pd <= 0 or pd >= 1:
            return {
                "status": "error",
                "error": "pd must be between 0 and 1",
                "timestamp": timestamp,
            }
        if lgd <= 0 or lgd > 1:
            return {
                "status": "error",
                "error": "lgd must be between 0 and 1",
                "timestamp": timestamp,
            }

        # Extract optional parameters
        maturity = float(args.get("maturity", 2.5))
        correlation = args.get("correlation")
        if correlation is not None:
            correlation = float(correlation)

        # Calculate regulatory capital
        result = calculate_regulatory_capital(
            exposure=exposure,
            pd=pd,
            lgd=lgd,
            maturity=maturity,
            correlation=correlation,
        )

        # Calculate capital ratio
        capital_ratio = result["regulatory_capital"] / exposure if exposure > 0 else 0

        return {
            "status": "success",
            "regulatory_capital": round(result["regulatory_capital"], 2),
            "risk_weighted_assets": round(result["risk_weighted_assets"], 2),
            "capital_requirement_k": round(result["capital_requirement_k"], 6),
            "expected_loss": round(result["expected_loss"], 2),
            "asset_correlation": round(result["asset_correlation"], 6),
            "maturity_adjustment": round(result["maturity_adjustment"], 6),
            "conditional_pd": round(result["conditional_pd"], 6),
            "capital_ratio": round(capital_ratio, 6),
            "capital_tier": get_capital_tier(capital_ratio),
            "exposure": exposure,
            "pd": pd,
            "lgd": lgd,
            "maturity": maturity,
            "model_version": "1.0",
            "methodology": "Basel_IRB_Corporate",
            "timestamp": timestamp,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "regulatory_capital": None,
            "timestamp": timestamp,
        }


# For local testing
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Regulatory Capital Model Endpoint - Test")
    print("=" * 50)

    # Sample test input
    test_input = {
        "exposure": 1000000,
        "pd": 0.05,
        "lgd": 0.45,
        "maturity": 3.0,
    }

    print(f"\nInput: {test_input}")

    result = predict(test_input)

    print(f"\nResults:")
    print(f"  Status: {result['status']}")
    print(f"  Regulatory Capital: ${result['regulatory_capital']:,.2f}")
    print(f"  Risk-Weighted Assets: ${result['risk_weighted_assets']:,.2f}")
    print(f"  Capital Requirement (K): {result['capital_requirement_k']:.4%}")
    print(f"  Expected Loss: ${result['expected_loss']:,.2f}")
    print(f"  Asset Correlation: {result['asset_correlation']:.4f}")
    print(f"  Capital Ratio: {result['capital_ratio']:.2%}")
    print(f"  Capital Tier: {result['capital_tier']}")

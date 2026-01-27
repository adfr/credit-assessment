#!/usr/bin/env python3
"""
CML Model Endpoint for VaR (Value at Risk)
Serves Monte Carlo VaR calculations for real-time risk assessment.
"""

import math
from typing import Optional
from datetime import datetime

import numpy as np
from scipy import stats


def calculate_var(
    exposure: float,
    pd: float,
    lgd: float,
    confidence: float = 0.999,
    simulations: int = 100000,
    correlation: float = 0.2,
    seed: int = 42
) -> dict:
    """
    Calculate Value at Risk (VaR) using Monte Carlo simulation.

    Args:
        exposure: Exposure at Default
        pd: Probability of Default (decimal)
        lgd: Loss Given Default (decimal)
        confidence: Confidence level
        simulations: Number of Monte Carlo simulations
        correlation: Asset correlation for systematic risk factor
        seed: Random seed for reproducibility

    Returns:
        dict with VaR calculation
    """
    np.random.seed(seed)

    # Constrain PD
    pd = max(0.0003, min(pd, 0.9999))

    # Default threshold (inverse normal of PD)
    threshold = stats.norm.ppf(pd)

    # Monte Carlo simulation with single-factor model
    losses = []

    for _ in range(simulations):
        # Systematic risk factor (market-wide shock)
        systematic = np.random.standard_normal()

        # Idiosyncratic factor (borrower-specific)
        idiosyncratic = np.random.standard_normal()

        # Combined factor
        z = math.sqrt(correlation) * systematic + math.sqrt(1 - correlation) * idiosyncratic

        # Default occurs if Z < threshold
        if z < threshold:
            loss = exposure * lgd
        else:
            loss = 0.0

        losses.append(loss)

    losses = np.array(losses)

    # Calculate statistics
    expected_loss = np.mean(losses)
    var = np.percentile(losses, confidence * 100)
    var_99 = np.percentile(losses, 99)
    var_95 = np.percentile(losses, 95)

    # Expected Shortfall (CVaR) - average loss beyond VaR
    tail_losses = losses[losses >= var]
    expected_shortfall = np.mean(tail_losses) if len(tail_losses) > 0 else var

    return {
        "var": var,
        "var_99": var_99,
        "var_95": var_95,
        "expected_loss": expected_loss,
        "expected_shortfall": expected_shortfall,
        "confidence": confidence,
        "simulations": simulations,
        "correlation": correlation,
        "exposure": exposure,
        "pd": pd,
        "lgd": lgd,
    }


def predict(args: dict) -> dict:
    """
    Main prediction function for CML endpoint.

    Args:
        args: Dictionary containing:
            - exposure: Exposure at Default (required)
            - pd: Probability of Default as decimal (required)
            - lgd: Loss Given Default as decimal (required)
            - confidence: Confidence level (default: 0.999)
            - simulations: Number of simulations (default: 100000)
            - correlation: Asset correlation (default: 0.2)

    Returns:
        Dictionary with VaR calculation results
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
        confidence = float(args.get("confidence", 0.999))
        simulations = int(args.get("simulations", 100000))
        correlation = float(args.get("correlation", 0.2))

        # Calculate VaR
        result = calculate_var(
            exposure=exposure,
            pd=pd,
            lgd=lgd,
            confidence=confidence,
            simulations=simulations,
            correlation=correlation,
        )

        return {
            "status": "success",
            "var": round(result["var"], 2),
            "var_99": round(result["var_99"], 2),
            "var_95": round(result["var_95"], 2),
            "expected_loss": round(result["expected_loss"], 2),
            "expected_shortfall": round(result["expected_shortfall"], 2),
            "confidence": confidence,
            "simulations": simulations,
            "correlation": correlation,
            "exposure": exposure,
            "pd": pd,
            "lgd": lgd,
            "model_version": "1.0",
            "timestamp": timestamp,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "var": None,
            "timestamp": timestamp,
        }


# For local testing
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("VaR Model Endpoint - Test")
    print("=" * 50)

    # Sample test input
    test_input = {
        "exposure": 1000000,
        "pd": 0.05,
        "lgd": 0.45,
        "confidence": 0.999,
        "simulations": 100000,
        "correlation": 0.2,
    }

    print(f"\nInput: {test_input}")

    result = predict(test_input)

    print(f"\nResults:")
    print(f"  Status: {result['status']}")
    print(f"  VaR (99.9%): ${result['var']:,.2f}")
    print(f"  VaR (99%): ${result['var_99']:,.2f}")
    print(f"  VaR (95%): ${result['var_95']:,.2f}")
    print(f"  Expected Loss: ${result['expected_loss']:,.2f}")
    print(f"  Expected Shortfall: ${result['expected_shortfall']:,.2f}")

#!/usr/bin/env python3
"""
Combined Risk Engine Endpoint
Orchestrates PD, LGD, and calculates comprehensive risk metrics.
"""

import os
import math
from pathlib import Path
from typing import Optional

import numpy as np

# Import model endpoints
from serve_pd import predict as predict_pd
from serve_lgd import predict as predict_lgd


# Risk calculation constants
CONFIDENCE_LEVEL = 0.999  # 99.9% for economic capital
BASEL_CORRELATION = 0.12  # Basel IRB correlation parameter
MATURITY_YEARS = 2.5  # Average maturity for capital calculation
COST_OF_FUNDS = 0.05  # 5% cost of funds
OPERATING_COST = 0.0025  # 25 bps operating cost


def calculate_expected_loss(pd: float, lgd: float, ead: float) -> float:
    """Calculate Expected Loss = PD × LGD × EAD."""
    return pd * lgd * ead


def calculate_unexpected_loss(pd: float, lgd: float, ead: float) -> float:
    """
    Calculate Unexpected Loss using Basel IRB-like formula.
    UL = EAD × LGD × (Conditional PD - PD)
    """
    # Correlation (simplified Basel II formula)
    r = BASEL_CORRELATION * (1 - np.exp(-50 * pd)) / (1 - np.exp(-50)) + \
        0.24 * (1 - (1 - np.exp(-50 * pd)) / (1 - np.exp(-50)))

    # Conditional PD (using normal distribution approximation)
    from scipy.stats import norm

    z_alpha = norm.ppf(CONFIDENCE_LEVEL)
    z_pd = norm.ppf(pd)

    conditional_pd = norm.cdf((z_pd + np.sqrt(r) * z_alpha) / np.sqrt(1 - r))
    conditional_pd = min(conditional_pd, 1.0)

    ul = ead * lgd * (conditional_pd - pd)
    return ul


def calculate_economic_capital(pd: float, lgd: float, ead: float) -> float:
    """Calculate Economic Capital at 99.9% confidence."""
    try:
        ul = calculate_unexpected_loss(pd, lgd, ead)
        # EC typically includes a buffer
        ec = ul * 1.1  # 10% buffer
        return ec
    except Exception:
        # Fallback calculation
        return ead * pd * lgd * 2.5


def calculate_regulatory_capital(pd: float, lgd: float, ead: float, maturity: float = 2.5) -> float:
    """
    Calculate Regulatory Capital using Basel IRB formula.
    """
    try:
        from scipy.stats import norm

        # Correlation
        r = 0.12 * (1 - np.exp(-50 * pd)) / (1 - np.exp(-50)) + \
            0.24 * (1 - (1 - np.exp(-50 * pd)) / (1 - np.exp(-50)))

        # Maturity adjustment
        b = (0.11852 - 0.05478 * np.log(pd)) ** 2
        maturity_adj = (1 + (maturity - 2.5) * b) / (1 - 1.5 * b)

        # Capital requirement
        z_alpha = norm.ppf(0.999)
        z_pd = norm.ppf(max(pd, 0.0003))

        conditional_pd = norm.cdf((z_pd + np.sqrt(r) * z_alpha) / np.sqrt(1 - r))
        k = (lgd * conditional_pd - pd * lgd) * maturity_adj

        rwa = k * 12.5 * ead  # Risk-weighted assets
        regulatory_capital = rwa * 0.08  # 8% capital requirement

        return regulatory_capital

    except Exception:
        # Fallback
        return ead * pd * lgd * 3


def calculate_rorac(
    net_income: float,
    expected_loss: float,
    economic_capital: float
) -> float:
    """
    Calculate RORAC (Return on Risk-Adjusted Capital).
    RORAC = (Net Income - Expected Loss) / Economic Capital
    """
    if economic_capital <= 0:
        return 0

    risk_adjusted_return = net_income - expected_loss
    rorac = risk_adjusted_return / economic_capital

    return rorac


def calculate_minimum_rate(
    pd: float,
    lgd: float,
    ead: float,
    ec: float,
    hurdle_rate: float = 0.15
) -> float:
    """Calculate minimum interest rate required."""
    el_premium = pd * lgd
    capital_charge = ec / ead * hurdle_rate

    min_rate = COST_OF_FUNDS + OPERATING_COST + el_premium + capital_charge + 0.005  # 50bp margin
    return min_rate


def get_decision_recommendation(
    pd: float,
    rorac: float,
    compliance_passed: bool = True
) -> dict:
    """Generate decision recommendation."""
    if not compliance_passed:
        return {
            "decision": "DECLINE",
            "reason": "Failed compliance checks",
            "auto_decidable": True,
        }

    if pd < 0.03 and rorac > 0.15:
        return {
            "decision": "APPROVE",
            "reason": "Low risk with acceptable returns",
            "auto_decidable": True,
        }
    elif pd > 0.15:
        return {
            "decision": "DECLINE",
            "reason": "High probability of default",
            "auto_decidable": True,
        }
    elif pd > 0.10:
        return {
            "decision": "REFER",
            "reason": "Elevated risk requires senior review",
            "auto_decidable": False,
        }
    elif rorac < 0.12:
        return {
            "decision": "REFER",
            "reason": "Marginal returns, consider pricing adjustment",
            "auto_decidable": False,
        }
    else:
        return {
            "decision": "REFER",
            "reason": "Standard review required",
            "auto_decidable": False,
        }


def score(args: dict) -> dict:
    """
    Main scoring function for Risk Engine endpoint.

    Args:
        args: Dictionary containing:
            Customer Features (for PD/LGD models):
            - debt_to_equity, current_ratio, interest_coverage_ratio, etc.

            Loan Parameters:
            - loan_amount: float (EAD)
            - interest_rate: float (proposed rate)
            - term_months: int
            - collateral_type: str

    Returns:
        Dictionary with complete risk assessment
    """
    try:
        # Extract loan parameters
        loan_amount = args.get("loan_amount", 1000000)
        interest_rate = args.get("interest_rate", 0.06)
        term_months = args.get("term_months", 36)

        # Get PD prediction
        pd_result = predict_pd(args)
        if pd_result["status"] != "success":
            return {
                "status": "error",
                "error": f"PD model error: {pd_result.get('error')}",
            }

        pd_score = pd_result["pd_score"]

        # Get LGD prediction
        lgd_result = predict_lgd(args)
        lgd_score = lgd_result.get("lgd_score", 0.45)  # Default if error

        # Use loan amount as EAD
        ead = loan_amount

        # Calculate risk metrics
        expected_loss = calculate_expected_loss(pd_score, lgd_score, ead)
        economic_capital = calculate_economic_capital(pd_score, lgd_score, ead)
        regulatory_capital = calculate_regulatory_capital(
            pd_score, lgd_score, ead, term_months / 12
        )

        # Calculate expected net income (simplified)
        annual_interest = loan_amount * interest_rate
        annual_costs = loan_amount * (COST_OF_FUNDS + OPERATING_COST)
        net_income = annual_interest - annual_costs

        # Calculate RORAC
        rorac = calculate_rorac(net_income, expected_loss, economic_capital)

        # Calculate minimum rate
        min_rate = calculate_minimum_rate(pd_score, lgd_score, ead, economic_capital)

        # Get decision recommendation
        recommendation = get_decision_recommendation(pd_score, rorac)

        # Risk grade from PD endpoint
        risk_grade = pd_result.get("risk_grade", "N/A")

        return {
            "status": "success",

            # Risk Scores
            "pd_score": round(pd_score, 6),
            "lgd_score": round(lgd_score, 6),
            "risk_grade": risk_grade,

            # Loss Metrics
            "expected_loss": round(expected_loss, 2),
            "expected_loss_rate": round(expected_loss / ead, 6),

            # Capital Metrics
            "economic_capital": round(economic_capital, 2),
            "regulatory_capital": round(regulatory_capital, 2),
            "capital_ratio": round(economic_capital / ead, 4),

            # Return Metrics
            "rorac": round(rorac, 4),
            "minimum_rate": round(min_rate, 4),
            "rate_adequacy": "ADEQUATE" if interest_rate >= min_rate else "INADEQUATE",

            # Decision
            "decision": recommendation["decision"],
            "decision_reason": recommendation["reason"],
            "auto_decidable": recommendation["auto_decidable"],

            # Loan Details
            "loan_amount": loan_amount,
            "proposed_rate": interest_rate,
            "term_months": term_months,
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Risk Engine Endpoint - Test")
    print("=" * 60)

    # Test input
    test_args = {
        # Loan parameters
        "loan_amount": 5000000,
        "interest_rate": 0.065,
        "term_months": 48,
        "collateral_type": "equipment",

        # Customer features
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
        "ltv_ratio": 0.7,
    }

    result = score(test_args)

    print(f"\nRisk Assessment Results:")
    print(f"  Status: {result['status']}")

    if result["status"] == "success":
        print(f"\n  Risk Scores:")
        print(f"    PD: {result['pd_score']:.4%}")
        print(f"    LGD: {result['lgd_score']:.4%}")
        print(f"    Risk Grade: {result['risk_grade']}")

        print(f"\n  Loss Metrics:")
        print(f"    Expected Loss: ${result['expected_loss']:,.2f}")
        print(f"    EL Rate: {result['expected_loss_rate']:.4%}")

        print(f"\n  Capital Requirements:")
        print(f"    Economic Capital: ${result['economic_capital']:,.2f}")
        print(f"    Regulatory Capital: ${result['regulatory_capital']:,.2f}")
        print(f"    Capital Ratio: {result['capital_ratio']:.2%}")

        print(f"\n  Return Analysis:")
        print(f"    RORAC: {result['rorac']:.2%}")
        print(f"    Minimum Rate: {result['minimum_rate']:.2%}")
        print(f"    Proposed Rate: {result['proposed_rate']:.2%}")
        print(f"    Rate Adequacy: {result['rate_adequacy']}")

        print(f"\n  Decision:")
        print(f"    Recommendation: {result['decision']}")
        print(f"    Reason: {result['decision_reason']}")
        print(f"    Auto-decidable: {result['auto_decidable']}")

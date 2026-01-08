"""
Loan-level tools for individual loan analysis
"""

from typing import Any, Optional
import sqlite3
from pathlib import Path

from .calculation_tools import (
    calculate_expected_loss,
    calculate_regulatory_capital,
    calculate_risk_grade,
)


def get_db_connection():
    """Get database connection"""
    db_path = Path(__file__).parent.parent.parent.parent / "data" / "credit_risk.db"
    return sqlite3.connect(str(db_path))


def get_loan_details(loan_id: str) -> dict[str, Any]:
    """
    Get comprehensive loan details

    Args:
        loan_id: Loan identifier

    Returns:
        dict with full loan information
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM loans WHERE loan_id = ?
        """, (loan_id,))
        row = cursor.fetchone()

        if not row:
            return {"error": f"Loan {loan_id} not found"}

        loan = dict(row)

        # Calculate risk metrics
        pd = loan.get("pd_score", 0.05)
        lgd = loan.get("lgd_score", 0.45)
        exposure = loan.get("outstanding_balance", 0)

        el_result = calculate_expected_loss(exposure, pd, lgd)
        cap_result = calculate_regulatory_capital(exposure, pd, lgd)
        grade_result = calculate_risk_grade(pd)

        loan.update({
            "expected_loss": el_result["expected_loss"],
            "regulatory_capital": cap_result["regulatory_capital"],
            "risk_weighted_assets": cap_result["risk_weighted_assets"],
            "risk_grade_info": grade_result,
        })

        return loan
    finally:
        conn.close()


def get_loan_risk_metrics(loan_id: str) -> dict[str, Any]:
    """
    Get risk metrics for a specific loan

    Args:
        loan_id: Loan identifier

    Returns:
        dict with all risk calculations
    """
    loan = get_loan_details(loan_id)

    if "error" in loan:
        return loan

    pd = loan.get("pd_score", 0.05)
    lgd = loan.get("lgd_score", 0.45)
    exposure = loan.get("outstanding_balance", 0)
    rate = loan.get("interest_rate", 0.05)

    # Import here to avoid circular imports
    from .calculation_tools import (
        calculate_expected_loss,
        calculate_regulatory_capital,
        calculate_economic_capital,
        calculate_var,
        calculate_rorac,
        calculate_risk_grade,
    )

    return {
        "loan_id": loan_id,
        "company_name": loan.get("company_name"),
        "exposure": exposure,
        "pd": pd,
        "lgd": lgd,
        "expected_loss": calculate_expected_loss(exposure, pd, lgd),
        "regulatory_capital": calculate_regulatory_capital(exposure, pd, lgd),
        "economic_capital": calculate_economic_capital(exposure, pd, lgd),
        "var_999": calculate_var(exposure, pd, lgd),
        "rorac": calculate_rorac(rate - 0.02, exposure, pd, lgd),
        "risk_grade": calculate_risk_grade(pd),
    }


def score_loan_pd(
    annual_revenue: float,
    net_income: float,
    total_assets: float,
    total_liabilities: float,
    years_in_business: int,
    industry: str,
    payment_history_score: float = 0.8
) -> dict[str, Any]:
    """
    Score a loan for PD using simplified model

    This is a placeholder that would normally call the ML model endpoint.
    Uses a simplified heuristic for demonstration.

    Args:
        annual_revenue: Annual revenue
        net_income: Net income
        total_assets: Total assets
        total_liabilities: Total liabilities
        years_in_business: Years in business
        industry: Industry sector
        payment_history_score: Payment history score (0-1)

    Returns:
        dict with PD score and contributing factors
    """
    # Calculate financial ratios
    profit_margin = net_income / annual_revenue if annual_revenue > 0 else 0
    leverage = total_liabilities / total_assets if total_assets > 0 else 1
    debt_to_revenue = total_liabilities / annual_revenue if annual_revenue > 0 else 1

    # Industry risk multipliers
    industry_risk = {
        "technology": 0.9,
        "healthcare": 0.85,
        "financial_services": 0.9,
        "manufacturing": 1.0,
        "retail": 1.1,
        "construction": 1.2,
        "hospitality": 1.3,
        "energy": 1.15,
    }.get(industry.lower(), 1.0)

    # Base PD calculation (simplified)
    base_pd = 0.05  # 5% baseline

    # Adjustments
    pd = base_pd

    # Profitability adjustment
    if profit_margin > 0.15:
        pd *= 0.7
    elif profit_margin > 0.05:
        pd *= 0.85
    elif profit_margin < 0:
        pd *= 1.5

    # Leverage adjustment
    if leverage > 0.8:
        pd *= 1.4
    elif leverage > 0.6:
        pd *= 1.1
    elif leverage < 0.4:
        pd *= 0.8

    # Experience adjustment
    if years_in_business > 10:
        pd *= 0.85
    elif years_in_business < 3:
        pd *= 1.3

    # Payment history adjustment
    pd *= (2 - payment_history_score)

    # Industry adjustment
    pd *= industry_risk

    # Constrain PD
    pd = max(0.001, min(pd, 0.50))

    # Get risk grade
    grade = calculate_risk_grade(pd)

    return {
        "pd_score": pd,
        "risk_grade": grade["risk_grade"],
        "factors": {
            "profit_margin": profit_margin,
            "leverage": leverage,
            "debt_to_revenue": debt_to_revenue,
            "years_in_business": years_in_business,
            "industry_risk": industry_risk,
            "payment_history_score": payment_history_score,
        },
        "adjustments": {
            "profitability_impact": "positive" if profit_margin > 0.05 else "negative",
            "leverage_impact": "negative" if leverage > 0.6 else "positive",
            "experience_impact": "positive" if years_in_business > 5 else "neutral",
        },
    }


def score_loan_lgd(
    collateral_type: str,
    collateral_value: float,
    exposure: float,
    seniority: str = "senior"
) -> dict[str, Any]:
    """
    Score a loan for LGD

    Args:
        collateral_type: Type of collateral
        collateral_value: Value of collateral
        exposure: Loan exposure
        seniority: Loan seniority (senior, subordinated)

    Returns:
        dict with LGD score and factors
    """
    # Base LGD by collateral type
    base_lgd = {
        "real_estate": 0.35,
        "equipment": 0.45,
        "inventory": 0.55,
        "receivables": 0.55,
        "securities": 0.40,
        "cash": 0.10,
        "unsecured": 0.75,
    }.get(collateral_type.lower(), 0.60)

    # Coverage ratio adjustment
    coverage = collateral_value / exposure if exposure > 0 else 0

    if coverage > 1.5:
        lgd = base_lgd * 0.6
    elif coverage > 1.0:
        lgd = base_lgd * 0.8
    elif coverage > 0.5:
        lgd = base_lgd * 0.95
    else:
        lgd = base_lgd * 1.1

    # Seniority adjustment
    if seniority.lower() == "subordinated":
        lgd *= 1.3

    # Constrain LGD
    lgd = max(0.05, min(lgd, 0.95))

    return {
        "lgd_score": lgd,
        "factors": {
            "collateral_type": collateral_type,
            "base_lgd": base_lgd,
            "coverage_ratio": coverage,
            "seniority": seniority,
        },
        "recovery_rate": 1 - lgd,
        "expected_recovery": collateral_value * (1 - lgd),
    }

"""
Loan-level tools for individual loan analysis
"""

import os
from typing import Any, Optional
import sqlite3
from pathlib import Path

from .calculation_tools import (
    calculate_expected_loss,
    calculate_regulatory_capital,
    calculate_risk_grade,
)

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))


def get_db_connection():
    """Get database connection"""
    db_path = PROJECT_ROOT / "data" / "credit_risk.db"
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


def list_loans(
    industry: str = None,
    risk_grade: str = None,
    payment_status: str = None,
    min_exposure: float = None,
    max_exposure: float = None,
    min_pd: float = None,
    max_pd: float = None,
    sort_by: str = "outstanding_balance",
    sort_order: str = "desc",
    limit: int = 1000
) -> dict[str, Any]:
    """
    List loans with optional filtering and sorting.

    Args:
        industry: Filter by industry (e.g., 'technology', 'healthcare')
        risk_grade: Filter by risk grade (e.g., 'A', 'B', 'C')
        payment_status: Filter by payment status (e.g., 'current', 'delinquent')
        min_exposure: Minimum outstanding balance
        max_exposure: Maximum outstanding balance
        min_pd: Minimum PD score
        max_pd: Maximum PD score
        sort_by: Field to sort by (outstanding_balance, pd_score, company_name)
        sort_order: Sort order ('asc' or 'desc')
        limit: Max number of loans to return (default 1000, max 10000)

    Returns:
        dict with loans list and summary statistics
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Build query
        query = "SELECT * FROM loans WHERE 1=1"
        params = []

        if industry:
            query += " AND industry = ?"
            params.append(industry)

        if risk_grade:
            query += " AND risk_grade = ?"
            params.append(risk_grade)

        if payment_status:
            query += " AND payment_status = ?"
            params.append(payment_status)

        if min_exposure is not None:
            query += " AND outstanding_balance >= ?"
            params.append(min_exposure)

        if max_exposure is not None:
            query += " AND outstanding_balance <= ?"
            params.append(max_exposure)

        if min_pd is not None:
            query += " AND pd_score >= ?"
            params.append(min_pd)

        if max_pd is not None:
            query += " AND pd_score <= ?"
            params.append(max_pd)

        # Validate sort field
        valid_sort_fields = ["outstanding_balance", "pd_score", "lgd_score", "company_name", "risk_grade", "industry"]
        if sort_by not in valid_sort_fields:
            sort_by = "outstanding_balance"

        sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"
        query += f" ORDER BY {sort_by} {sort_order}"

        # Limit
        limit = min(limit, 10000)
        query += f" LIMIT {limit}"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        loans = []
        for row in rows:
            loan = dict(row)
            # Calculate expected loss for each loan
            pd = loan.get("pd_score", 0.05)
            lgd = loan.get("lgd_score", 0.45)
            exposure = loan.get("outstanding_balance", 0)
            loan["expected_loss"] = exposure * pd * lgd
            loans.append(loan)

        # Calculate summary statistics
        if loans:
            total_exposure = sum(l.get("outstanding_balance", 0) for l in loans)
            total_el = sum(l.get("expected_loss", 0) for l in loans)
            avg_pd = sum(l.get("pd_score", 0) for l in loans) / len(loans)
            avg_lgd = sum(l.get("lgd_score", 0) for l in loans) / len(loans)
        else:
            total_exposure = total_el = avg_pd = avg_lgd = 0

        return {
            "loans": loans,
            "count": len(loans),
            "filters_applied": {
                "industry": industry,
                "risk_grade": risk_grade,
                "payment_status": payment_status,
                "min_exposure": min_exposure,
                "max_exposure": max_exposure,
                "min_pd": min_pd,
                "max_pd": max_pd,
            },
            "summary": {
                "total_exposure": total_exposure,
                "total_expected_loss": total_el,
                "avg_pd": avg_pd,
                "avg_lgd": avg_lgd,
            }
        }
    finally:
        conn.close()


def get_top_exposures(limit: int = 10) -> dict[str, Any]:
    """
    Get the top largest exposures in the portfolio.

    Args:
        limit: Number of top exposures to return (default 10)

    Returns:
        dict with top exposures and risk metrics
    """
    return list_loans(sort_by="outstanding_balance", sort_order="desc", limit=limit)


def get_high_risk_loans(pd_threshold: float = 0.10, limit: int = 20) -> dict[str, Any]:
    """
    Get loans with PD above a threshold.

    Args:
        pd_threshold: PD threshold (default 0.10 = 10%)
        limit: Max number of loans to return

    Returns:
        dict with high-risk loans
    """
    return list_loans(min_pd=pd_threshold, sort_by="pd_score", sort_order="desc", limit=limit)


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

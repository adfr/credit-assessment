"""
Portfolio-level tools for the reasoning agent
"""

from typing import Any
import sqlite3
from pathlib import Path


def get_db_connection():
    """Get database connection"""
    db_path = Path(__file__).parent.parent.parent.parent / "data" / "credit_risk.db"
    return sqlite3.connect(str(db_path))


def get_portfolio_summary() -> dict[str, Any]:
    """
    Get portfolio summary statistics including:
    - Total exposure and loan count
    - Average PD, LGD, interest rate
    - Expected loss and capital metrics
    - Payment status breakdown
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                COUNT(*) as loan_count,
                SUM(outstanding_balance) as total_exposure,
                SUM(original_balance) as total_original,
                AVG(pd_score) as avg_pd,
                AVG(lgd_score) as avg_lgd,
                AVG(interest_rate) as avg_rate,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_count,
                SUM(CASE WHEN status = 'defaulted' THEN 1 ELSE 0 END) as defaulted_count,
                SUM(CASE WHEN payment_status = 'current' THEN 1 ELSE 0 END) as current_count,
                SUM(CASE WHEN payment_status = 'delinquent' THEN 1 ELSE 0 END) as delinquent_count,
                SUM(CASE WHEN payment_status = 'default' THEN 1 ELSE 0 END) as default_count
            FROM loans
        """)
        row = cursor.fetchone()

        if row and row["total_exposure"]:
            total_exposure = row["total_exposure"]
            avg_pd = row["avg_pd"] or 0.05
            avg_lgd = row["avg_lgd"] or 0.45

            # Calculate capital metrics
            expected_loss = total_exposure * avg_pd * avg_lgd
            regulatory_capital = total_exposure * avg_pd * avg_lgd * 8  # Simplified Basel
            economic_capital = expected_loss * 2.5  # Simplified EC
            var_999 = expected_loss * 3.0  # Simplified VaR
            risk_weighted_assets = total_exposure * avg_pd * 12.5

            return {
                "loan_count": row["loan_count"],
                "total_exposure": total_exposure,
                "total_original": row["total_original"],
                "avg_pd": avg_pd * 100,
                "avg_lgd": avg_lgd * 100,
                "avg_rate": (row["avg_rate"] or 0) * 100,
                "active_count": row["active_count"],
                "defaulted_count": row["defaulted_count"],
                "current_count": row["current_count"],
                "delinquent_count": row["delinquent_count"],
                "default_count": row["default_count"],
                "expected_loss": expected_loss,
                "regulatory_capital": regulatory_capital,
                "economic_capital": economic_capital,
                "var_999": var_999,
                "risk_weighted_assets": risk_weighted_assets,
                "reg_capital_ratio": (regulatory_capital / total_exposure * 100) if total_exposure > 0 else 0,
                "econ_capital_ratio": (economic_capital / total_exposure * 100) if total_exposure > 0 else 0,
            }
        return {}
    finally:
        conn.close()


def get_concentration_analysis(dimension: str = "industry") -> dict[str, Any]:
    """
    Get concentration analysis by dimension (industry, region, risk_grade)
    Returns HHI index and breakdown
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    valid_dimensions = ["industry", "region", "risk_grade"]
    if dimension not in valid_dimensions:
        dimension = "industry"

    try:
        cursor.execute(f"""
            SELECT
                {dimension} as category,
                COUNT(*) as count,
                SUM(outstanding_balance) as exposure,
                AVG(pd_score) as avg_pd,
                AVG(lgd_score) as avg_lgd
            FROM loans
            WHERE status = 'active'
            GROUP BY {dimension}
            ORDER BY exposure DESC
        """)
        rows = cursor.fetchall()

        total_exposure = sum(row["exposure"] for row in rows)
        breakdown = []
        hhi = 0

        for row in rows:
            pct = (row["exposure"] / total_exposure * 100) if total_exposure > 0 else 0
            hhi += pct ** 2
            breakdown.append({
                "category": row["category"],
                "count": row["count"],
                "exposure": row["exposure"],
                "percentage": pct,
                "avg_pd": (row["avg_pd"] or 0) * 100,
                "avg_lgd": (row["avg_lgd"] or 0) * 100,
            })

        concentration_level = "Low" if hhi < 1500 else "Moderate" if hhi < 2500 else "High"

        return {
            "dimension": dimension,
            "hhi": hhi,
            "concentration_level": concentration_level,
            "breakdown": breakdown,
            "total_exposure": total_exposure,
        }
    finally:
        conn.close()


def get_risk_distribution() -> dict[str, Any]:
    """Get distribution by risk grade"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                risk_grade,
                COUNT(*) as count,
                SUM(outstanding_balance) as exposure,
                AVG(pd_score) as avg_pd
            FROM loans
            WHERE status = 'active'
            GROUP BY risk_grade
            ORDER BY
                CASE risk_grade
                    WHEN 'AAA' THEN 1
                    WHEN 'AA' THEN 2
                    WHEN 'A' THEN 3
                    WHEN 'BBB' THEN 4
                    WHEN 'BB' THEN 5
                    WHEN 'B' THEN 6
                    WHEN 'CCC' THEN 7
                    WHEN 'CC' THEN 8
                    WHEN 'C' THEN 9
                    WHEN 'D' THEN 10
                    ELSE 11
                END
        """)
        rows = cursor.fetchall()

        total_exposure = sum(row["exposure"] for row in rows)
        distribution = []

        for row in rows:
            pct = (row["exposure"] / total_exposure * 100) if total_exposure > 0 else 0
            distribution.append({
                "risk_grade": row["risk_grade"],
                "count": row["count"],
                "exposure": row["exposure"],
                "percentage": pct,
                "avg_pd": (row["avg_pd"] or 0) * 100,
            })

        return {
            "distribution": distribution,
            "total_exposure": total_exposure,
        }
    finally:
        conn.close()


def get_large_exposures(threshold_pct: float = 5.0) -> dict[str, Any]:
    """Get loans exceeding threshold percentage of portfolio"""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT SUM(outstanding_balance) as total FROM loans WHERE status = 'active'")
        total = cursor.fetchone()["total"] or 0
        threshold_amount = total * (threshold_pct / 100)

        cursor.execute("""
            SELECT
                loan_id, company_name, industry, outstanding_balance,
                risk_grade, pd_score
            FROM loans
            WHERE status = 'active' AND outstanding_balance >= ?
            ORDER BY outstanding_balance DESC
        """, (threshold_amount,))
        rows = cursor.fetchall()

        exposures = []
        total_large = 0

        for row in rows:
            pct = (row["outstanding_balance"] / total * 100) if total > 0 else 0
            total_large += row["outstanding_balance"]
            exposures.append({
                "loan_id": row["loan_id"],
                "company_name": row["company_name"],
                "industry": row["industry"],
                "outstanding_balance": row["outstanding_balance"],
                "percentage": pct,
                "risk_grade": row["risk_grade"],
                "pd_score": (row["pd_score"] or 0) * 100,
            })

        return {
            "threshold_pct": threshold_pct,
            "threshold_amount": threshold_amount,
            "total_exposure": total,
            "count": len(exposures),
            "exposures": exposures,
            "total_large_exposure": total_large,
            "large_exposure_pct": (total_large / total * 100) if total > 0 else 0,
        }
    finally:
        conn.close()

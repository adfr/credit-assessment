"""
Portfolio Service
Portfolio-level analytics and aggregations.
"""

import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from .capital_service import get_capital_service


# Database path
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
DB_PATH = PROJECT_ROOT / "data" / "credit_risk.db"


class PortfolioService:
    """Service for portfolio analytics and aggregations."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.capital_service = get_capital_service()

    def _get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def _dict_factory(self, cursor, row):
        """Convert rows to dictionaries."""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    # =========================================================================
    # Portfolio Summary
    # =========================================================================

    def get_portfolio_summary(self) -> Dict:
        """Get dashboard summary metrics."""
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()

        # Basic aggregations
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
        summary = cursor.fetchone()

        # Get all loans for capital calculations
        cursor.execute("SELECT * FROM loans")
        loans = cursor.fetchall()
        conn.close()

        # Calculate capital metrics
        capital = self.capital_service.get_portfolio_capital_summary(loans)

        return {
            "loan_count": summary["loan_count"],
            "total_exposure": round(summary["total_exposure"] or 0, 2),
            "total_original": round(summary["total_original"] or 0, 2),
            "avg_pd": round((summary["avg_pd"] or 0) * 100, 2),  # As percentage
            "avg_lgd": round((summary["avg_lgd"] or 0) * 100, 2),
            "avg_rate": round((summary["avg_rate"] or 0) * 100, 2),
            "active_count": summary["active_count"],
            "defaulted_count": summary["defaulted_count"],
            "current_count": summary["current_count"],
            "delinquent_count": summary["delinquent_count"],
            "default_count": summary["default_count"],

            # Capital metrics
            "regulatory_capital": capital["regulatory_capital"],
            "economic_capital": capital["economic_capital"],
            "expected_loss": capital["expected_loss"],
            "var_999": capital["var_999"],
            "risk_weighted_assets": capital["risk_weighted_assets"],
            "reg_capital_ratio": capital["reg_capital_ratio"],
            "econ_capital_ratio": capital["econ_capital_ratio"],
        }

    # =========================================================================
    # Risk Distribution
    # =========================================================================

    def get_risk_distribution(self) -> Dict:
        """Get risk grade distribution for charts."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                risk_grade,
                COUNT(*) as count,
                SUM(outstanding_balance) as exposure,
                AVG(pd_score) as avg_pd
            FROM loans
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
                    ELSE 8
                END
        """)

        results = cursor.fetchall()
        conn.close()

        total_exposure = sum(r[2] or 0 for r in results)

        distribution = []
        for risk_grade, count, exposure, avg_pd in results:
            distribution.append({
                "risk_grade": risk_grade,
                "count": count,
                "exposure": round(exposure or 0, 2),
                "percentage": round((exposure or 0) / total_exposure * 100, 2) if total_exposure > 0 else 0,
                "avg_pd": round((avg_pd or 0) * 100, 2),
            })

        return {
            "distribution": distribution,
            "total_exposure": round(total_exposure, 2),
        }

    # =========================================================================
    # Concentration Analysis
    # =========================================================================

    def calculate_hhi(self, shares: List[float]) -> float:
        """
        Calculate Herfindahl-Hirschman Index.
        HHI = sum of squared market shares
        Range: 0 to 10000 (when shares are percentages)
        """
        return sum(s ** 2 for s in shares)

    def get_concentration_analysis(self, dimension: str) -> Dict:
        """
        Get concentration analysis by dimension.
        Dimensions: industry, region, risk_grade, maturity, collateral
        """
        valid_dimensions = {
            "industry": "industry",
            "region": "region",
            "risk_grade": "risk_grade",
            "collateral": "collateral_type",
            "purpose": "purpose",
        }

        if dimension not in valid_dimensions:
            return {"error": f"Invalid dimension. Use one of: {list(valid_dimensions.keys())}"}

        column = valid_dimensions[dimension]

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT
                {column} as category,
                COUNT(*) as count,
                SUM(outstanding_balance) as exposure,
                AVG(pd_score) as avg_pd,
                AVG(lgd_score) as avg_lgd
            FROM loans
            GROUP BY {column}
            ORDER BY SUM(outstanding_balance) DESC
        """)

        results = cursor.fetchall()

        # Get total
        cursor.execute("SELECT SUM(outstanding_balance) FROM loans")
        total_exposure = cursor.fetchone()[0] or 0

        conn.close()

        breakdown = []
        shares = []

        for category, count, exposure, avg_pd, avg_lgd in results:
            pct = (exposure or 0) / total_exposure * 100 if total_exposure > 0 else 0
            shares.append(pct)

            breakdown.append({
                "category": category or "Unknown",
                "count": count,
                "exposure": round(exposure or 0, 2),
                "percentage": round(pct, 2),
                "avg_pd": round((avg_pd or 0) * 100, 2),
                "avg_lgd": round((avg_lgd or 0) * 100, 2),
            })

        hhi = self.calculate_hhi(shares)

        # HHI interpretation
        if hhi < 1500:
            concentration_level = "Low"
        elif hhi < 2500:
            concentration_level = "Moderate"
        else:
            concentration_level = "High"

        return {
            "dimension": dimension,
            "hhi": round(hhi, 2),
            "concentration_level": concentration_level,
            "breakdown": breakdown,
            "total_exposure": round(total_exposure, 2),
        }

    # =========================================================================
    # Large Exposures
    # =========================================================================

    def get_large_exposures(self, threshold_pct: float = 5.0) -> Dict:
        """
        Get loans exceeding threshold percentage of portfolio.
        """
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()

        # Get total exposure
        cursor.execute("SELECT SUM(outstanding_balance) FROM loans")
        total_exposure = cursor.fetchone()["SUM(outstanding_balance)"] or 0

        threshold_amount = total_exposure * (threshold_pct / 100)

        # Get large exposures
        cursor.execute("""
            SELECT *
            FROM loans
            WHERE outstanding_balance >= ?
            ORDER BY outstanding_balance DESC
        """, (threshold_amount,))

        large_loans = cursor.fetchall()
        conn.close()

        exposures = []
        for loan in large_loans:
            exposures.append({
                "loan_id": loan["loan_id"],
                "company_name": loan["company_name"],
                "industry": loan["industry"],
                "outstanding_balance": loan["outstanding_balance"],
                "percentage": round(loan["outstanding_balance"] / total_exposure * 100, 2),
                "risk_grade": loan["risk_grade"],
                "pd_score": round(loan["pd_score"] * 100, 2),
            })

        return {
            "threshold_pct": threshold_pct,
            "threshold_amount": round(threshold_amount, 2),
            "total_exposure": round(total_exposure, 2),
            "count": len(exposures),
            "exposures": exposures,
            "total_large_exposure": round(sum(e["outstanding_balance"] for e in exposures), 2),
            "large_exposure_pct": round(sum(e["percentage"] for e in exposures), 2),
        }

    # =========================================================================
    # Risk Migration Matrix
    # =========================================================================

    def get_risk_migration_matrix(self, period_months: int = 12) -> Dict:
        """
        Get risk rating transition matrix.
        Note: In a real system, this would track actual grade changes over time.
        Here we simulate based on current data patterns.
        """
        # Define transition probabilities (simplified)
        # In production, this would be calculated from historical grade changes
        grades = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "Default"]

        # Simulated transition matrix (rows: from, cols: to)
        # These are typical 1-year transition rates
        matrix = {
            "AAA": {"AAA": 90.0, "AA": 8.0, "A": 1.5, "BBB": 0.3, "BB": 0.1, "B": 0.05, "CCC": 0.03, "Default": 0.02},
            "AA": {"AAA": 2.0, "AA": 88.0, "A": 8.0, "BBB": 1.5, "BB": 0.3, "B": 0.1, "CCC": 0.05, "Default": 0.05},
            "A": {"AAA": 0.1, "AA": 3.0, "A": 87.0, "BBB": 7.5, "BB": 1.5, "B": 0.5, "CCC": 0.2, "Default": 0.2},
            "BBB": {"AAA": 0.05, "AA": 0.3, "A": 5.0, "BBB": 84.0, "BB": 7.5, "B": 2.0, "CCC": 0.75, "Default": 0.4},
            "BB": {"AAA": 0.02, "AA": 0.1, "A": 0.5, "BBB": 6.0, "BB": 78.0, "B": 10.0, "CCC": 3.5, "Default": 1.88},
            "B": {"AAA": 0.01, "AA": 0.05, "A": 0.2, "BBB": 0.5, "BB": 5.0, "B": 75.0, "CCC": 12.0, "Default": 7.24},
            "CCC": {"AAA": 0.0, "AA": 0.02, "A": 0.1, "BBB": 0.3, "BB": 1.0, "B": 8.0, "CCC": 65.0, "Default": 25.58},
        }

        return {
            "period_months": period_months,
            "grades": grades,
            "matrix": matrix,
            "note": "Simulated transition rates based on typical credit migration patterns",
        }

    # =========================================================================
    # Vintage Analysis
    # =========================================================================

    def get_vintage_analysis(self) -> Dict:
        """
        Get default rates by origination vintage (year/quarter).
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                strftime('%Y-Q', disbursement_date,
                    CASE
                        WHEN CAST(strftime('%m', disbursement_date) AS INTEGER) <= 3 THEN '1'
                        WHEN CAST(strftime('%m', disbursement_date) AS INTEGER) <= 6 THEN '2'
                        WHEN CAST(strftime('%m', disbursement_date) AS INTEGER) <= 9 THEN '3'
                        ELSE '4'
                    END
                ) as vintage,
                strftime('%Y', disbursement_date) as year,
                COUNT(*) as loan_count,
                SUM(original_balance) as original_volume,
                SUM(outstanding_balance) as current_exposure,
                SUM(CASE WHEN status = 'defaulted' OR payment_status = 'default' THEN 1 ELSE 0 END) as default_count,
                SUM(CASE WHEN status = 'defaulted' OR payment_status = 'default' THEN outstanding_balance ELSE 0 END) as default_exposure,
                AVG(pd_score) as avg_pd
            FROM loans
            GROUP BY strftime('%Y', disbursement_date)
            ORDER BY year DESC
        """)

        results = cursor.fetchall()
        conn.close()

        vintages = []
        for vintage, year, count, original, current, defaults, default_exp, avg_pd in results:
            default_rate = (defaults / count * 100) if count > 0 else 0
            loss_rate = (default_exp / original * 100) if original > 0 else 0

            vintages.append({
                "vintage": year,
                "loan_count": count,
                "original_volume": round(original or 0, 2),
                "current_exposure": round(current or 0, 2),
                "default_count": defaults,
                "default_rate": round(default_rate, 2),
                "default_exposure": round(default_exp or 0, 2),
                "loss_rate": round(loss_rate, 2),
                "avg_pd": round((avg_pd or 0) * 100, 2),
            })

        return {
            "vintages": vintages,
            "total_vintages": len(vintages),
        }

    # =========================================================================
    # Loan Operations
    # =========================================================================

    def list_loans(
        self,
        status: str = None,
        risk_grade: str = None,
        industry: str = None,
        region: str = None,
        payment_status: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """List loans with optional filtering."""
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()

        # Build query with filters
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if risk_grade:
            conditions.append("risk_grade = ?")
            params.append(risk_grade)
        if industry:
            conditions.append("industry = ?")
            params.append(industry)
        if region:
            conditions.append("region = ?")
            params.append(region)
        if payment_status:
            conditions.append("payment_status = ?")
            params.append(payment_status)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get count
        cursor.execute(f"SELECT COUNT(*) as total FROM loans WHERE {where_clause}", params)
        total = cursor.fetchone()["total"]

        # Get loans
        cursor.execute(f"""
            SELECT * FROM loans
            WHERE {where_clause}
            ORDER BY outstanding_balance DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])

        loans = cursor.fetchall()
        conn.close()

        return {
            "loans": loans,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_loan(self, loan_id: str) -> Optional[Dict]:
        """Get single loan by ID."""
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM loans WHERE loan_id = ?", (loan_id,))
        loan = cursor.fetchone()
        conn.close()

        return loan

    def get_loan_repayments(self, loan_id: str) -> List[Dict]:
        """Get repayment history for a loan."""
        conn = self._get_connection()
        conn.row_factory = self._dict_factory
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM repayments
            WHERE loan_id = ?
            ORDER BY payment_date DESC
        """, (loan_id,))

        repayments = cursor.fetchall()
        conn.close()

        return repayments

    def add_loan(self, loan_data: Dict) -> Dict:
        """Add a new loan to the portfolio."""
        import uuid

        conn = self._get_connection()
        cursor = conn.cursor()

        loan_id = f"LOAN-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO loans (
                loan_id, company_name, industry, region, country,
                original_balance, outstanding_balance, interest_rate, term_months,
                purpose, collateral_type, collateral_value,
                disbursement_date, maturity_date,
                last_payment_date, last_payment_amount, days_past_due, payment_status,
                status, pd_score, lgd_score, risk_grade,
                annual_revenue, net_income, total_assets, total_liabilities,
                submitted_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            loan_id,
            loan_data.get("company_name"),
            loan_data.get("industry"),
            loan_data.get("region"),
            loan_data.get("country"),
            loan_data.get("loan_amount", 0),
            loan_data.get("loan_amount", 0),  # Outstanding = original initially
            loan_data.get("interest_rate", 0.05),
            loan_data.get("term_months", 36),
            loan_data.get("purpose"),
            loan_data.get("collateral_type", "unsecured"),
            loan_data.get("collateral_value", 0),
            loan_data.get("disbursement_date", now[:10]),
            loan_data.get("maturity_date"),
            None,  # last_payment_date
            0,  # last_payment_amount
            0,  # days_past_due
            "current",  # payment_status
            "active",  # status
            loan_data.get("pd_score", 0.05),
            loan_data.get("lgd_score", 0.45),
            loan_data.get("risk_grade", "BBB"),
            loan_data.get("annual_revenue", 0),
            loan_data.get("net_income", 0),
            loan_data.get("total_assets", 0),
            loan_data.get("total_liabilities", 0),
            now,
            now,
        ))

        conn.commit()
        conn.close()

        return {"loan_id": loan_id, "message": "Loan added successfully"}


# Singleton instance
_portfolio_service = None


def get_portfolio_service() -> PortfolioService:
    """Get singleton instance of PortfolioService."""
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService()
    return _portfolio_service

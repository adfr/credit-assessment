"""
Iceberg/Database Service
Handles database operations for the Credit Risk Platform.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import json


class IcebergService:
    """Service for database operations."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "credit_risk.db"
        self.db_path = str(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # Application Operations
    def save_application(self, application_data: dict) -> str:
        """Save a new application."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO applications (
                application_id, company_name, industry, requested_amount,
                requested_term_months, purpose, collateral_type, collateral_value,
                annual_revenue, net_income, total_assets, total_liabilities,
                status, documents_json, submitted_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            application_data["application_id"],
            application_data.get("company_name"),
            application_data.get("industry"),
            application_data.get("requested_amount"),
            application_data.get("requested_term_months"),
            application_data.get("purpose"),
            application_data.get("collateral_type"),
            application_data.get("collateral_value"),
            application_data.get("annual_revenue"),
            application_data.get("net_income"),
            application_data.get("total_assets"),
            application_data.get("total_liabilities"),
            "pending",
            json.dumps(application_data.get("documents", [])),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ))

        conn.commit()
        conn.close()
        return application_data["application_id"]

    def get_application(self, application_id: str) -> Optional[dict]:
        """Get application by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def list_applications(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """List applications with optional filtering."""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM applications"
        params = []

        if status:
            query += " WHERE status = ?"
            params.append(status)

        query += " ORDER BY submitted_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def update_application_status(
        self,
        application_id: str,
        status: str,
        workflow_id: Optional[str] = None
    ):
        """Update application status."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if workflow_id:
            cursor.execute("""
                UPDATE applications
                SET status = ?, workflow_id = ?, updated_at = ?
                WHERE application_id = ?
            """, (status, workflow_id, datetime.now().isoformat(), application_id))
        else:
            cursor.execute("""
                UPDATE applications
                SET status = ?, updated_at = ?
                WHERE application_id = ?
            """, (status, datetime.now().isoformat(), application_id))

        conn.commit()
        conn.close()

    # Prediction Operations
    def save_prediction(self, prediction_data: dict):
        """Save model prediction for audit trail."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO predictions (
                application_id, model_version, pd_score, lgd_score, ead,
                expected_loss, economic_capital, regulatory_capital, rorac,
                features_json, model_decision, predicted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction_data["application_id"],
            prediction_data.get("model_version", "1.0"),
            prediction_data.get("pd_score"),
            prediction_data.get("lgd_score"),
            prediction_data.get("ead"),
            prediction_data.get("expected_loss"),
            prediction_data.get("economic_capital"),
            prediction_data.get("regulatory_capital"),
            prediction_data.get("rorac"),
            json.dumps(prediction_data.get("features", {})),
            prediction_data.get("model_decision"),
            datetime.now().isoformat(),
        ))

        conn.commit()
        conn.close()

    # Decision Operations
    def save_decision(self, decision_data: dict):
        """Save final decision."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO decisions (
                application_id, final_decision, decision_type, decision_reason,
                conditions_json, approved_by, approved_amount, approved_rate,
                approved_term_months, pd_at_decision, lgd_at_decision,
                el_at_decision, decided_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_data["application_id"],
            decision_data["final_decision"],
            decision_data.get("decision_type", "auto"),
            decision_data.get("decision_reason"),
            json.dumps(decision_data.get("conditions", [])),
            decision_data.get("approved_by", "system"),
            decision_data.get("approved_amount"),
            decision_data.get("approved_rate"),
            decision_data.get("approved_term_months"),
            decision_data.get("pd_at_decision"),
            decision_data.get("lgd_at_decision"),
            decision_data.get("el_at_decision"),
            datetime.now().isoformat(),
        ))

        conn.commit()
        conn.close()

    def get_decision(self, application_id: str) -> Optional[dict]:
        """Get decision for application."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM decisions WHERE application_id = ?", (application_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    # Historical Data Operations
    def get_customer_history(self, company_id: str) -> dict:
        """Get historical data for a customer."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get company info
        cursor.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,))
        company = cursor.fetchone()

        # Get loan history
        cursor.execute("""
            SELECT * FROM loan_history WHERE company_id = ?
            ORDER BY origination_date DESC
        """, (company_id,))
        loans = cursor.fetchall()

        # Get bureau history
        cursor.execute("""
            SELECT * FROM bureau_data WHERE company_id = ?
            ORDER BY report_date DESC LIMIT 1
        """, (company_id,))
        bureau = cursor.fetchone()

        conn.close()

        return {
            "company": dict(company) if company else None,
            "loans": [dict(l) for l in loans] if loans else [],
            "bureau": dict(bureau) if bureau else None,
        }

    def get_industry_benchmarks(self, industry: str) -> dict:
        """Get industry benchmarks."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                industry,
                AVG(default_flag) as default_rate,
                AVG(annual_revenue) as avg_revenue,
                COUNT(*) as company_count
            FROM companies c
            JOIN loan_history l ON c.company_id = l.company_id
            WHERE c.industry = ?
            GROUP BY c.industry
        """, (industry,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return {
            "industry": industry,
            "default_rate": 0.05,
            "avg_revenue": 50000000,
            "company_count": 0,
        }

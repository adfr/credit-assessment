"""
Alert Handler
Manages alerts for model monitoring and system health.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertHandler:
    """Handles alerting for model monitoring."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            project_root = Path(__file__).parent.parent
            db_path = project_root / "data" / "credit_risk.db"
        self.db_path = str(db_path)
        self._ensure_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self):
        """Ensure the alerts table exists."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                source TEXT,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TEXT,
                resolved INTEGER DEFAULT 0,
                resolved_at TEXT,
                created_at TEXT NOT NULL,
                metadata_json TEXT
            )
        """)
        conn.commit()
        conn.close()

    def create_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        source: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """Create a new alert."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO alerts (
                alert_type, severity, title, message, source,
                created_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            alert_type,
            severity,
            title,
            message,
            source,
            datetime.now().isoformat(),
            json.dumps(metadata or {}),
        ))

        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.warning(f"[{severity.upper()}] {title}: {message}")

        return alert_id

    def acknowledge_alert(self, alert_id: int, acknowledged_by: str):
        """Acknowledge an alert."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE alerts
            SET acknowledged = 1, acknowledged_by = ?, acknowledged_at = ?
            WHERE id = ?
        """, (acknowledged_by, datetime.now().isoformat(), alert_id))

        conn.commit()
        conn.close()

        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")

    def resolve_alert(self, alert_id: int):
        """Resolve an alert."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE alerts
            SET resolved = 1, resolved_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), alert_id))

        conn.commit()
        conn.close()

        logger.info(f"Alert {alert_id} resolved")

    def get_active_alerts(
        self,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None
    ) -> List[Dict]:
        """Get all active (unresolved) alerts."""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM alerts WHERE resolved = 0"
        params = []

        if severity:
            query += " AND severity = ?"
            params.append(severity)

        if alert_type:
            query += " AND alert_type = ?"
            params.append(alert_type)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_alert_history(
        self,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict]:
        """Get alert history."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT * FROM alerts
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (cutoff_date, limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_alert_summary(self) -> Dict:
        """Get summary of current alerts."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Count by severity
        cursor.execute("""
            SELECT severity, COUNT(*) as count
            FROM alerts
            WHERE resolved = 0
            GROUP BY severity
        """)
        by_severity = {row["severity"]: row["count"] for row in cursor.fetchall()}

        # Count by type
        cursor.execute("""
            SELECT alert_type, COUNT(*) as count
            FROM alerts
            WHERE resolved = 0
            GROUP BY alert_type
        """)
        by_type = {row["alert_type"]: row["count"] for row in cursor.fetchall()}

        # Total active
        cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE resolved = 0")
        total_active = cursor.fetchone()["count"]

        # Unacknowledged
        cursor.execute("""
            SELECT COUNT(*) as count FROM alerts
            WHERE resolved = 0 AND acknowledged = 0
        """)
        unacknowledged = cursor.fetchone()["count"]

        conn.close()

        return {
            "total_active": total_active,
            "unacknowledged": unacknowledged,
            "by_severity": by_severity,
            "by_type": by_type,
        }

    # Convenience methods for creating specific alert types
    def drift_alert(
        self,
        feature: str,
        psi_value: float,
        threshold: float,
        model_name: str = "pd_model"
    ):
        """Create a drift detection alert."""
        severity = "critical" if psi_value > 0.25 else "warning"

        return self.create_alert(
            alert_type="drift",
            severity=severity,
            title=f"Feature Drift Detected: {feature}",
            message=f"PSI value ({psi_value:.3f}) exceeds threshold ({threshold})",
            source=model_name,
            metadata={
                "feature": feature,
                "psi_value": psi_value,
                "threshold": threshold,
            }
        )

    def performance_alert(
        self,
        metric_name: str,
        current_value: float,
        threshold: float,
        model_name: str
    ):
        """Create a performance degradation alert."""
        return self.create_alert(
            alert_type="performance",
            severity="warning",
            title=f"Performance Degradation: {metric_name}",
            message=f"Current value ({current_value:.4f}) crossed threshold ({threshold})",
            source=model_name,
            metadata={
                "metric": metric_name,
                "current_value": current_value,
                "threshold": threshold,
            }
        )

    def system_alert(
        self,
        title: str,
        message: str,
        severity: str = "info"
    ):
        """Create a system health alert."""
        return self.create_alert(
            alert_type="system",
            severity=severity,
            title=title,
            message=message,
            source="system",
        )

    def compliance_alert(
        self,
        issue: str,
        application_id: str,
        regulation: str
    ):
        """Create a compliance issue alert."""
        return self.create_alert(
            alert_type="compliance",
            severity="critical",
            title=f"Compliance Issue: {issue}",
            message=f"Application {application_id} has compliance concerns",
            source="compliance_engine",
            metadata={
                "application_id": application_id,
                "regulation": regulation,
            }
        )


def main():
    """Test the alert handler."""
    handler = AlertHandler()

    # Create test alerts
    print("Creating test alerts...")

    handler.drift_alert("credit_score", 0.15, 0.10)
    handler.performance_alert("auc", 0.78, 0.80, "pd_model")
    handler.system_alert("High API Latency", "Average latency increased to 500ms", "warning")

    # Get active alerts
    print("\nActive Alerts:")
    for alert in handler.get_active_alerts():
        print(f"  [{alert['severity']}] {alert['title']}")

    # Get summary
    print("\nAlert Summary:")
    summary = handler.get_alert_summary()
    print(f"  Total Active: {summary['total_active']}")
    print(f"  Unacknowledged: {summary['unacknowledged']}")
    print(f"  By Severity: {summary['by_severity']}")
    print(f"  By Type: {summary['by_type']}")


if __name__ == "__main__":
    main()

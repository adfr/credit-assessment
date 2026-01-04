"""
Performance Tracker
Tracks model performance metrics over time.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Tracks and stores model performance metrics."""

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
        """Ensure the performance metrics table exists."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                model_version TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                sample_size INTEGER,
                recorded_at TEXT NOT NULL,
                metadata_json TEXT
            )
        """)
        conn.commit()
        conn.close()

    def record_metric(
        self,
        model_name: str,
        model_version: str,
        metric_name: str,
        metric_value: float,
        sample_size: Optional[int] = None,
        metadata: Optional[Dict] = None
    ):
        """Record a performance metric."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO model_performance (
                model_name, model_version, metric_name, metric_value,
                sample_size, recorded_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            model_name,
            model_version,
            metric_name,
            metric_value,
            sample_size,
            datetime.now().isoformat(),
            json.dumps(metadata or {}),
        ))

        conn.commit()
        conn.close()

        logger.info(
            f"Recorded {metric_name}={metric_value:.4f} for {model_name} v{model_version}"
        )

    def get_latest_metrics(
        self,
        model_name: str,
        model_version: Optional[str] = None
    ) -> Dict[str, float]:
        """Get the latest metrics for a model."""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT metric_name, metric_value
            FROM model_performance
            WHERE model_name = ?
        """
        params = [model_name]

        if model_version:
            query += " AND model_version = ?"
            params.append(model_version)

        query += """
            AND recorded_at = (
                SELECT MAX(recorded_at) FROM model_performance
                WHERE model_name = ?
            )
        """
        params.append(model_name)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return {row["metric_name"]: row["metric_value"] for row in rows}

    def get_metric_history(
        self,
        model_name: str,
        metric_name: str,
        days: int = 30
    ) -> List[Dict]:
        """Get metric history for the specified period."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT metric_value, recorded_at, sample_size
            FROM model_performance
            WHERE model_name = ? AND metric_name = ? AND recorded_at >= ?
            ORDER BY recorded_at ASC
        """, (model_name, metric_name, cutoff_date))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def check_performance_thresholds(
        self,
        model_name: str,
        thresholds: Dict[str, Dict[str, float]]
    ) -> List[Dict]:
        """Check if current metrics violate thresholds."""
        current_metrics = self.get_latest_metrics(model_name)
        violations = []

        for metric_name, bounds in thresholds.items():
            if metric_name not in current_metrics:
                continue

            value = current_metrics[metric_name]
            min_val = bounds.get("min")
            max_val = bounds.get("max")

            if min_val is not None and value < min_val:
                violations.append({
                    "metric": metric_name,
                    "current_value": value,
                    "threshold": f"min={min_val}",
                    "severity": "warning" if value >= min_val * 0.95 else "critical",
                })

            if max_val is not None and value > max_val:
                violations.append({
                    "metric": metric_name,
                    "current_value": value,
                    "threshold": f"max={max_val}",
                    "severity": "warning" if value <= max_val * 1.05 else "critical",
                })

        return violations

    def calculate_trend(
        self,
        model_name: str,
        metric_name: str,
        days: int = 7
    ) -> Dict:
        """Calculate trend for a metric."""
        history = self.get_metric_history(model_name, metric_name, days)

        if len(history) < 2:
            return {"trend": "insufficient_data", "change": 0}

        first_value = history[0]["metric_value"]
        last_value = history[-1]["metric_value"]
        change = (last_value - first_value) / first_value if first_value != 0 else 0

        if abs(change) < 0.01:
            trend = "stable"
        elif change > 0:
            trend = "improving" if metric_name in ["auc", "gini", "r2"] else "degrading"
        else:
            trend = "degrading" if metric_name in ["auc", "gini", "r2"] else "improving"

        return {
            "trend": trend,
            "change": change,
            "first_value": first_value,
            "last_value": last_value,
            "data_points": len(history),
        }

    def generate_performance_report(self, model_name: str) -> Dict:
        """Generate a comprehensive performance report."""
        current_metrics = self.get_latest_metrics(model_name)

        report = {
            "model_name": model_name,
            "generated_at": datetime.now().isoformat(),
            "current_metrics": current_metrics,
            "trends": {},
            "health_status": "healthy",
        }

        # Calculate trends for key metrics
        for metric_name in current_metrics.keys():
            report["trends"][metric_name] = self.calculate_trend(
                model_name, metric_name, days=7
            )

        # Check for degrading trends
        degrading_count = sum(
            1 for t in report["trends"].values()
            if t.get("trend") == "degrading"
        )

        if degrading_count >= 2:
            report["health_status"] = "warning"
        elif degrading_count >= 3:
            report["health_status"] = "critical"

        return report


# Default thresholds for credit risk models
DEFAULT_THRESHOLDS = {
    "pd_model": {
        "auc": {"min": 0.75},
        "gini": {"min": 0.50},
        "ks": {"min": 0.30},
    },
    "lgd_model": {
        "mse": {"max": 0.05},
        "r2": {"min": 0.70},
    },
}


def main():
    """Test the performance tracker."""
    tracker = PerformanceTracker()

    # Record some test metrics
    tracker.record_metric("pd_model", "1.0", "auc", 0.847)
    tracker.record_metric("pd_model", "1.0", "gini", 0.694)
    tracker.record_metric("pd_model", "1.0", "ks", 0.521)

    tracker.record_metric("lgd_model", "1.0", "mse", 0.0234)
    tracker.record_metric("lgd_model", "1.0", "r2", 0.782)

    # Get latest metrics
    print("\nPD Model Metrics:")
    print(tracker.get_latest_metrics("pd_model"))

    print("\nLGD Model Metrics:")
    print(tracker.get_latest_metrics("lgd_model"))

    # Check thresholds
    print("\nThreshold Violations:")
    violations = tracker.check_performance_thresholds(
        "pd_model", DEFAULT_THRESHOLDS["pd_model"]
    )
    print(violations if violations else "None")

    # Generate report
    print("\nPerformance Report:")
    report = tracker.generate_performance_report("pd_model")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

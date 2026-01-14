"""
Model Registry Service

Manages multiple ML models for PD and LGD predictions.
Supports model versioning, activation, and metadata tracking.
"""

import os
import json
import uuid
import pickle
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum


class ModelType(str, Enum):
    PD = "pd"
    LGD = "lgd"


class ModelStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANDIDATE = "candidate"
    DEPRECATED = "deprecated"


@dataclass
class ModelMetadata:
    model_id: str
    model_type: str  # "pd" or "lgd"
    model_name: str
    version: str
    framework: str  # sklearn, xgboost, lightgbm, etc.
    file_path: str
    status: str
    training_date: str
    created_at: str
    updated_at: str
    description: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    feature_names: Optional[List[str]] = None
    hyperparameters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelRegistryService:
    """Service for managing ML model registry."""

    def __init__(self):
        project_root = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
        self.db_path = project_root / "data" / "credit_risk.db"
        self.models_dir = project_root / "data" / "models"
        self._ensure_tables()
        self._register_existing_models()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self):
        """Create model registry tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Model metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_registry (
                model_id TEXT PRIMARY KEY,
                model_type TEXT NOT NULL,
                model_name TEXT NOT NULL,
                version TEXT NOT NULL,
                framework TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'inactive',
                training_date TEXT,
                description TEXT,
                metrics_json TEXT,
                feature_names_json TEXT,
                hyperparameters_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(model_type, model_name, version)
            )
        """)

        # Model predictions audit table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_predictions_audit (
                prediction_id TEXT PRIMARY KEY,
                loan_id TEXT,
                model_id TEXT NOT NULL,
                model_type TEXT NOT NULL,
                score REAL NOT NULL,
                confidence REAL,
                features_json TEXT,
                predicted_at TEXT NOT NULL,
                FOREIGN KEY (model_id) REFERENCES model_registry(model_id)
            )
        """)

        conn.commit()
        conn.close()

    def _register_existing_models(self):
        """Register existing model files that aren't in the registry."""
        # Check for PD models
        pd_dir = self.models_dir / "pd"
        if pd_dir.exists():
            for model_file in pd_dir.glob("*.pkl"):
                self._register_model_file(model_file, ModelType.PD)

        # Check for LGD models
        lgd_dir = self.models_dir / "lgd"
        if lgd_dir.exists():
            for model_file in lgd_dir.glob("*.pkl"):
                self._register_model_file(model_file, ModelType.LGD)

    def _register_model_file(self, file_path: Path, model_type: ModelType):
        """Register a model file if not already registered."""
        # Parse model name and version from filename
        # Expected format: model_name_version.pkl or model_name.pkl
        filename = file_path.stem

        # Skip if already registered by file path
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT model_id FROM model_registry WHERE file_path = ?",
            (str(file_path),)
        )
        if cursor.fetchone():
            conn.close()
            return

        # Parse filename
        if "_latest" in filename:
            model_name = filename.replace("_latest", "")
            version = "latest"
        else:
            parts = filename.rsplit("_", 1)
            if len(parts) == 2 and parts[1].replace(".", "").isdigit():
                model_name = parts[0]
                version = parts[1]
            else:
                model_name = filename
                version = "1.0"

        # Try to extract metadata from pickle
        metrics = None
        framework = "sklearn"
        try:
            with open(file_path, "rb") as f:
                model_data = pickle.load(f)
                if isinstance(model_data, dict):
                    metrics = model_data.get("metrics")
                    framework = model_data.get("framework", "sklearn")
        except Exception:
            pass

        # Determine status - latest models are active
        status = ModelStatus.ACTIVE if "latest" in filename else ModelStatus.INACTIVE

        now = datetime.now().isoformat()
        model_id = str(uuid.uuid4())

        cursor.execute("""
            INSERT OR IGNORE INTO model_registry (
                model_id, model_type, model_name, version, framework,
                file_path, status, training_date, metrics_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model_id, model_type.value, model_name, version, framework,
            str(file_path), status.value, now, json.dumps(metrics) if metrics else None,
            now, now
        ))

        conn.commit()
        conn.close()

    def register_model(
        self,
        model_type: ModelType,
        model_name: str,
        version: str,
        file_path: str,
        framework: str = "sklearn",
        description: str = None,
        metrics: Dict[str, float] = None,
        feature_names: List[str] = None,
        hyperparameters: Dict[str, Any] = None,
        training_date: str = None,
        activate: bool = False
    ) -> ModelMetadata:
        """Register a new model in the registry."""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        model_id = str(uuid.uuid4())
        status = ModelStatus.ACTIVE if activate else ModelStatus.INACTIVE

        # If activating, deactivate other models of same type
        if activate:
            cursor.execute(
                "UPDATE model_registry SET status = ?, updated_at = ? WHERE model_type = ? AND status = ?",
                (ModelStatus.INACTIVE.value, now, model_type.value, ModelStatus.ACTIVE.value)
            )

        cursor.execute("""
            INSERT INTO model_registry (
                model_id, model_type, model_name, version, framework,
                file_path, status, training_date, description,
                metrics_json, feature_names_json, hyperparameters_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model_id, model_type.value, model_name, version, framework,
            file_path, status.value, training_date or now, description,
            json.dumps(metrics) if metrics else None,
            json.dumps(feature_names) if feature_names else None,
            json.dumps(hyperparameters) if hyperparameters else None,
            now, now
        ))

        conn.commit()
        conn.close()

        return self.get_model(model_id)

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM model_registry WHERE model_id = ?", (model_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_metadata(row)

    def get_active_model(self, model_type: ModelType) -> Optional[ModelMetadata]:
        """Get the currently active model for a given type."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM model_registry WHERE model_type = ? AND status = ? LIMIT 1",
            (model_type.value, ModelStatus.ACTIVE.value)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_metadata(row)

    def list_models(
        self,
        model_type: Optional[ModelType] = None,
        status: Optional[ModelStatus] = None
    ) -> List[ModelMetadata]:
        """List all models, optionally filtered by type and status."""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM model_registry WHERE 1=1"
        params = []

        if model_type:
            query += " AND model_type = ?"
            params.append(model_type.value)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY model_type, created_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_metadata(row) for row in rows]

    def activate_model(self, model_id: str) -> bool:
        """Set a model as active, deactivating others of the same type."""
        model = self.get_model(model_id)
        if not model:
            return False

        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        # Deactivate other models of same type
        cursor.execute(
            "UPDATE model_registry SET status = ?, updated_at = ? WHERE model_type = ? AND status = ?",
            (ModelStatus.INACTIVE.value, now, model.model_type, ModelStatus.ACTIVE.value)
        )

        # Activate the specified model
        cursor.execute(
            "UPDATE model_registry SET status = ?, updated_at = ? WHERE model_id = ?",
            (ModelStatus.ACTIVE.value, now, model_id)
        )

        conn.commit()
        conn.close()
        return True

    def deactivate_model(self, model_id: str) -> bool:
        """Deactivate a model."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute(
            "UPDATE model_registry SET status = ?, updated_at = ? WHERE model_id = ?",
            (ModelStatus.INACTIVE.value, now, model_id)
        )

        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def update_model_metrics(self, model_id: str, metrics: Dict[str, float]) -> bool:
        """Update model performance metrics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute(
            "UPDATE model_registry SET metrics_json = ?, updated_at = ? WHERE model_id = ?",
            (json.dumps(metrics), now, model_id)
        )

        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def load_model(self, model_id: str) -> Optional[Any]:
        """Load the actual model object from file."""
        model_meta = self.get_model(model_id)
        if not model_meta:
            return None

        try:
            with open(model_meta.file_path, "rb") as f:
                model_data = pickle.load(f)
                # Handle both raw model and dict format
                if isinstance(model_data, dict) and "model" in model_data:
                    return model_data["model"]
                return model_data
        except Exception as e:
            print(f"Error loading model {model_id}: {e}")
            return None

    def load_active_model(self, model_type: ModelType) -> Optional[Any]:
        """Load the currently active model for a given type."""
        model_meta = self.get_active_model(model_type)
        if not model_meta:
            return None
        return self.load_model(model_meta.model_id)

    def log_prediction(
        self,
        model_id: str,
        model_type: ModelType,
        loan_id: str,
        score: float,
        confidence: float = None,
        features: Dict[str, Any] = None
    ):
        """Log a prediction for audit purposes."""
        conn = self._get_connection()
        cursor = conn.cursor()

        prediction_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO model_predictions_audit (
                prediction_id, loan_id, model_id, model_type,
                score, confidence, features_json, predicted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction_id, loan_id, model_id, model_type.value,
            score, confidence, json.dumps(features) if features else None, now
        ))

        conn.commit()
        conn.close()

    def get_prediction_history(
        self,
        model_id: str = None,
        loan_id: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get prediction history, optionally filtered."""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM model_predictions_audit WHERE 1=1"
        params = []

        if model_id:
            query += " AND model_id = ?"
            params.append(model_id)

        if loan_id:
            query += " AND loan_id = ?"
            params.append(loan_id)

        query += " ORDER BY predicted_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def _row_to_metadata(self, row: sqlite3.Row) -> ModelMetadata:
        """Convert database row to ModelMetadata."""
        return ModelMetadata(
            model_id=row["model_id"],
            model_type=row["model_type"],
            model_name=row["model_name"],
            version=row["version"],
            framework=row["framework"],
            file_path=row["file_path"],
            status=row["status"],
            training_date=row["training_date"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            description=row["description"],
            metrics=json.loads(row["metrics_json"]) if row["metrics_json"] else None,
            feature_names=json.loads(row["feature_names_json"]) if row["feature_names_json"] else None,
            hyperparameters=json.loads(row["hyperparameters_json"]) if row["hyperparameters_json"] else None,
        )


# Singleton instance
_registry_instance = None


def get_model_registry() -> ModelRegistryService:
    """Get or create the model registry singleton."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ModelRegistryService()
    return _registry_instance

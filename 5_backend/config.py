"""
Configuration for Credit Risk Platform Backend

Uses the centralized config system from /config directory.
Loads local.yaml or production.yaml based on APP_ENV environment variable.

Usage:
    from config import settings, is_production, is_local

    # Access settings
    db_url = settings.database_url
    debug = settings.api_debug

    # Check environment
    if is_production():
        # Production-specific logic
        pass
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

# Add project root to path for config import
project_root = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))

# Import from the config package at project root (avoid name collision with this module)
_config_loader_path = project_root / "config" / "config_loader.py"
_spec = importlib.util.spec_from_file_location("app_config_loader", _config_loader_path)
_config_loader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config_loader)

# Extract functions from the loaded module
get_config = _config_loader.get_config
get_environment = _config_loader.get_environment
get_nested = _config_loader.get_nested
is_production = _config_loader.is_production
is_local = _config_loader.is_local


def _get_yaml_config():
    """Get the YAML configuration, with fallback for import errors."""
    try:
        return get_config()
    except Exception:
        # Return empty dict if config loading fails (e.g., during initial setup)
        return {}


class Settings(BaseSettings):
    """Application settings combining YAML config with environment overrides."""

    # Load YAML config
    _yaml_config: dict = {}

    def __init__(self, **kwargs):
        # Load YAML config before Pydantic initialization
        yaml_cfg = _get_yaml_config()

        # Set defaults from YAML config
        # CML environment variables take priority
        cml_port = os.environ.get("CDSW_APP_PORT", os.environ.get("CDSW_READONLY_PORT"))

        defaults = {
            "api_host": os.environ.get("API_HOST", get_nested(yaml_cfg, "api", "host", default="127.0.0.1")),
            "api_port": int(cml_port) if cml_port else get_nested(yaml_cfg, "api", "port", default=8090),
            "api_debug": get_nested(yaml_cfg, "api", "debug", default=False),
            "database_url": get_nested(yaml_cfg, "database", "url", default=f"sqlite:///{project_root}/data/credit_risk.db"),
            "redis_url": get_nested(yaml_cfg, "redis", "url", default="redis://localhost:6379"),
            "use_redis": get_nested(yaml_cfg, "redis", "enabled", default=False),
            "use_local_models": get_nested(yaml_cfg, "models", "use_local", default=True),
            "mlflow_tracking_uri": get_nested(yaml_cfg, "mlflow", "tracking_uri", default="./mlruns"),
            "mlflow_experiment_name": get_nested(yaml_cfg, "mlflow", "experiment_name", default=None),
            "mlflow_registry_uri": get_nested(yaml_cfg, "mlflow", "registry_uri", default=None),
            "mlflow_tracking_username": get_nested(yaml_cfg, "mlflow", "tracking_username", default=None),
            "mlflow_tracking_password": get_nested(yaml_cfg, "mlflow", "tracking_password", default=None),
            "mlflow_tracking_token": get_nested(yaml_cfg, "mlflow", "tracking_token", default=None),
            "chroma_persist_directory": get_nested(yaml_cfg, "chromadb", "persist_directory", default=str(project_root / "data" / "chroma_db")),
            "workflow_timeout_seconds": get_nested(yaml_cfg, "workflow", "timeout_seconds", default=300),
            "max_retries": get_nested(yaml_cfg, "workflow", "max_retries", default=3),
            "pd_auto_approve_threshold": get_nested(yaml_cfg, "thresholds", "pd_auto_approve", default=0.03),
            "pd_auto_decline_threshold": get_nested(yaml_cfg, "thresholds", "pd_auto_decline", default=0.15),
            "pd_refer_threshold": get_nested(yaml_cfg, "thresholds", "pd_refer", default=0.10),
            "min_rorac_threshold": get_nested(yaml_cfg, "thresholds", "min_rorac", default=0.12),
            "cors_origins": get_nested(yaml_cfg, "cors", "origins", default=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"]),
            "log_level": get_nested(yaml_cfg, "logging", "level", default="INFO"),
            "ssl_enabled": get_nested(yaml_cfg, "security", "ssl_enabled", default=False),
            "rate_limiting_enabled": get_nested(yaml_cfg, "security", "rate_limiting_enabled", default=False),
        }

        # Merge with any kwargs provided
        for key, value in defaults.items():
            if key not in kwargs:
                kwargs[key] = value

        super().__init__(**kwargs)
        self._yaml_config = yaml_cfg

    # Environment
    app_env: str = get_environment()

    # API Configuration - use CML environment variables if available
    api_host: str = os.environ.get("API_HOST", "127.0.0.1")
    api_port: int = int(os.environ.get("CDSW_APP_PORT", os.environ.get("CDSW_READONLY_PORT", "8090")))
    api_debug: bool = False

    # Project paths
    project_root: Path = project_root
    data_dir: Path = project_root / "data"

    # Database
    database_url: str = f"sqlite:///{project_root}/data/credit_risk.db"

    # Redis (for LangGraph checkpointing)
    redis_url: str = "redis://localhost:6379"
    use_redis: bool = False

    # Claude API
    anthropic_api_key: Optional[str] = None

    # Model Endpoints (for CML deployment)
    pd_model_endpoint: Optional[str] = None
    lgd_model_endpoint: Optional[str] = None
    document_endpoint: Optional[str] = None
    rag_endpoint: Optional[str] = None

    # Use local models instead of endpoints
    use_local_models: bool = True

    # MLflow Configuration
    mlflow_tracking_uri: str = "./mlruns"
    mlflow_experiment_name: Optional[str] = None
    mlflow_registry_uri: Optional[str] = None
    mlflow_tracking_username: Optional[str] = None
    mlflow_tracking_password: Optional[str] = None
    mlflow_tracking_token: Optional[str] = None

    # ChromaDB
    chroma_persist_directory: str = str(project_root / "data" / "chroma_db")

    # Workflow settings
    workflow_timeout_seconds: int = 300
    max_retries: int = 3

    # Decision thresholds
    pd_auto_approve_threshold: float = 0.03
    pd_auto_decline_threshold: float = 0.15
    pd_refer_threshold: float = 0.10
    min_rorac_threshold: float = 0.12

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"]

    # Security
    ssl_enabled: bool = False
    rate_limiting_enabled: bool = False

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_model_endpoints(self) -> dict[str, Optional[str]]:
        """Get model endpoint configuration from YAML or env vars."""
        yaml_endpoints = get_nested(self._yaml_config, "models", "endpoints", default={})
        return {
            "pd": self.pd_model_endpoint or yaml_endpoints.get("pd"),
            "lgd": self.lgd_model_endpoint or yaml_endpoints.get("lgd"),
            "document": self.document_endpoint or yaml_endpoints.get("document"),
            "rag": self.rag_endpoint or yaml_endpoints.get("rag"),
        }

    def get_model_paths(self) -> dict[str, Path]:
        """Get model file paths from YAML config."""
        yaml_paths = get_nested(self._yaml_config, "models", "paths", default={})
        return {
            "pd": Path(yaml_paths.get("pd", self.data_dir / "models" / "pd" / "pd_model_latest.pkl")),
            "lgd": Path(yaml_paths.get("lgd", self.data_dir / "models" / "lgd" / "lgd_model_latest.pkl")),
        }

    def configure_mlflow(self) -> dict[str, str]:
        """
        Configure MLflow tracking with environment-aware settings.

        Returns dict with MLflow configuration for logging/debugging.
        Sets up tracking URI and authentication based on environment.

        Usage:
            from config import settings
            mlflow_info = settings.configure_mlflow()
            # MLflow is now configured - use mlflow.* functions
        """
        try:
            import mlflow
        except ImportError:
            return {
                "status": "error",
                "message": "MLflow not installed. Run: pip install mlflow",
                "tracking_uri": None,
            }

        # Set tracking URI
        tracking_uri = self.mlflow_tracking_uri
        mlflow.set_tracking_uri(tracking_uri)

        # Set registry URI if different from tracking URI
        if self.mlflow_registry_uri:
            mlflow.set_registry_uri(self.mlflow_registry_uri)

        # Configure authentication for Cloudera MLflow (production)
        auth_info = {}
        if is_production() and tracking_uri.startswith("http"):
            # Set authentication via environment variables for MLflow client
            if self.mlflow_tracking_username and self.mlflow_tracking_password:
                os.environ["MLFLOW_TRACKING_USERNAME"] = self.mlflow_tracking_username
                os.environ["MLFLOW_TRACKING_PASSWORD"] = self.mlflow_tracking_password
                auth_info["auth_method"] = "basic"
            elif self.mlflow_tracking_token:
                os.environ["MLFLOW_TRACKING_TOKEN"] = self.mlflow_tracking_token
                auth_info["auth_method"] = "token"

        # Set experiment if configured
        if self.mlflow_experiment_name:
            mlflow.set_experiment(self.mlflow_experiment_name)

        return {
            "status": "configured",
            "tracking_uri": tracking_uri,
            "registry_uri": self.mlflow_registry_uri or tracking_uri,
            "experiment_name": self.mlflow_experiment_name,
            "environment": self.app_env,
            **auth_info,
        }


# Create settings instance
settings = Settings()


# Model paths (using new method)
MODEL_PATHS = settings.get_model_paths()


# Industry risk tiers
INDUSTRY_RISK_TIERS = {
    "technology": 2,
    "healthcare": 1,
    "manufacturing": 3,
    "retail": 4,
    "financial_services": 1,
    "energy": 4,
    "construction": 5,
    "transportation": 3,
    "hospitality": 5,
    "professional_services": 2,
}


# LGD assumptions by collateral type
LGD_ASSUMPTIONS = {
    "real_estate": 0.35,
    "equipment": 0.45,
    "inventory": 0.55,
    "receivables": 0.55,
    "securities": 0.40,
    "unsecured": 0.75,
}


def get_model_path(model_type: str) -> Path:
    """Get path to model file."""
    return MODEL_PATHS.get(model_type)


def get_industry_risk_tier(industry: str) -> int:
    """Get risk tier for an industry."""
    return INDUSTRY_RISK_TIERS.get(industry.lower(), 3)


def get_lgd_assumption(collateral_type: str) -> float:
    """Get LGD assumption for collateral type."""
    return LGD_ASSUMPTIONS.get(collateral_type.lower(), 0.75)


# Re-export environment helpers
__all__ = [
    "settings",
    "Settings",
    "is_production",
    "is_local",
    "get_model_path",
    "get_industry_risk_tier",
    "get_lgd_assumption",
    "MODEL_PATHS",
    "INDUSTRY_RISK_TIERS",
    "LGD_ASSUMPTIONS",
]

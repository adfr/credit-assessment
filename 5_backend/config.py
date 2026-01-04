"""
Configuration for Credit Risk Platform Backend
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False

    # Project paths
    project_root: Path = Path(__file__).parent.parent
    data_dir: Path = project_root / "data"

    # Database
    database_url: str = f"sqlite:///{project_root}/data/credit_risk.db"

    # Redis (for LangGraph checkpointing)
    redis_url: str = "redis://localhost:6379"
    use_redis: bool = False  # Set to True if Redis is available

    # Claude API
    anthropic_api_key: Optional[str] = None

    # Model Endpoints (for CML deployment)
    pd_model_endpoint: Optional[str] = None
    lgd_model_endpoint: Optional[str] = None
    document_endpoint: Optional[str] = None
    rag_endpoint: Optional[str] = None

    # Use local models instead of endpoints
    use_local_models: bool = True

    # MLflow
    mlflow_tracking_uri: str = "./mlruns"

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
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Create settings instance
settings = Settings()


# Model paths
MODEL_PATHS = {
    "pd": settings.data_dir / "models" / "pd" / "pd_model_latest.pkl",
    "lgd": settings.data_dir / "models" / "lgd" / "lgd_model_latest.pkl",
}


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

"""
Model Management API

Endpoints for managing ML models - listing, activation, metrics.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from services.model_registry_service import (
    get_model_registry,
    ModelType,
    ModelStatus,
    ModelMetadata,
)

router = APIRouter(prefix="/api/models", tags=["models"])


class ModelResponse(BaseModel):
    model_id: str
    model_type: str
    model_name: str
    version: str
    framework: str
    status: str
    training_date: Optional[str]
    description: Optional[str]
    metrics: Optional[Dict[str, float]]
    created_at: str
    updated_at: str


class ModelListResponse(BaseModel):
    models: List[ModelResponse]
    total: int


class ModelActivateRequest(BaseModel):
    model_id: str


class ModelMetricsUpdate(BaseModel):
    metrics: Dict[str, float]


def _metadata_to_response(meta: ModelMetadata) -> ModelResponse:
    """Convert ModelMetadata to API response."""
    return ModelResponse(
        model_id=meta.model_id,
        model_type=meta.model_type,
        model_name=meta.model_name,
        version=meta.version,
        framework=meta.framework,
        status=meta.status,
        training_date=meta.training_date,
        description=meta.description,
        metrics=meta.metrics,
        created_at=meta.created_at,
        updated_at=meta.updated_at,
    )


@router.get("", response_model=ModelListResponse)
async def list_models(
    model_type: Optional[str] = Query(None, description="Filter by model type (pd/lgd)"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List all registered models."""
    registry = get_model_registry()

    type_filter = ModelType(model_type) if model_type else None
    status_filter = ModelStatus(status) if status else None

    models = registry.list_models(model_type=type_filter, status=status_filter)

    return ModelListResponse(
        models=[_metadata_to_response(m) for m in models],
        total=len(models),
    )


@router.get("/active", response_model=Dict[str, Optional[ModelResponse]])
async def get_active_models():
    """Get currently active PD and LGD models."""
    registry = get_model_registry()

    pd_model = registry.get_active_model(ModelType.PD)
    lgd_model = registry.get_active_model(ModelType.LGD)

    return {
        "pd": _metadata_to_response(pd_model) if pd_model else None,
        "lgd": _metadata_to_response(lgd_model) if lgd_model else None,
    }


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: str):
    """Get details for a specific model."""
    registry = get_model_registry()
    model = registry.get_model(model_id)

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return _metadata_to_response(model)


@router.post("/{model_id}/activate")
async def activate_model(model_id: str):
    """Activate a model (deactivates others of same type)."""
    registry = get_model_registry()

    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    success = registry.activate_model(model_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to activate model")

    return {
        "message": f"Model {model.model_name} v{model.version} activated",
        "model_id": model_id,
        "model_type": model.model_type,
    }


@router.post("/{model_id}/deactivate")
async def deactivate_model(model_id: str):
    """Deactivate a model."""
    registry = get_model_registry()

    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    success = registry.deactivate_model(model_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to deactivate model")

    return {
        "message": f"Model {model.model_name} v{model.version} deactivated",
        "model_id": model_id,
    }


@router.put("/{model_id}/metrics")
async def update_model_metrics(model_id: str, update: ModelMetricsUpdate):
    """Update model performance metrics."""
    registry = get_model_registry()

    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    success = registry.update_model_metrics(model_id, update.metrics)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update metrics")

    return {
        "message": "Metrics updated",
        "model_id": model_id,
        "metrics": update.metrics,
    }


@router.get("/{model_id}/predictions")
async def get_model_predictions(
    model_id: str,
    limit: int = Query(100, le=1000),
):
    """Get prediction history for a model."""
    registry = get_model_registry()

    model = registry.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    predictions = registry.get_prediction_history(model_id=model_id, limit=limit)

    return {
        "model_id": model_id,
        "predictions": predictions,
        "count": len(predictions),
    }


@router.get("/compare/{model_type}")
async def compare_models(
    model_type: str,
    model_ids: str = Query(..., description="Comma-separated model IDs to compare"),
):
    """Compare metrics between multiple models."""
    registry = get_model_registry()

    ids = [id.strip() for id in model_ids.split(",")]
    comparison = []

    for model_id in ids:
        model = registry.get_model(model_id)
        if model and model.model_type == model_type:
            comparison.append({
                "model_id": model.model_id,
                "model_name": model.model_name,
                "version": model.version,
                "status": model.status,
                "metrics": model.metrics or {},
                "training_date": model.training_date,
            })

    return {
        "model_type": model_type,
        "comparison": comparison,
        "count": len(comparison),
    }

"""
Applications API Routes
CRUD operations for credit applications.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import uuid
from datetime import datetime

from models.application import ApplicationCreate, ApplicationResponse
from services.iceberg_service import IcebergService

router = APIRouter(prefix="/applications", tags=["applications"])

db_service = IcebergService()


@router.post("/", response_model=dict)
async def create_application(application: ApplicationCreate):
    """Create a new credit application."""
    try:
        application_id = str(uuid.uuid4())

        application_data = {
            "application_id": application_id,
            "company_name": application.company_name,
            "industry": application.industry,
            "requested_amount": application.requested_amount,
            "requested_term_months": application.requested_term_months,
            "purpose": application.purpose,
            "collateral_type": application.collateral_type,
            "collateral_value": application.collateral_value,
            "annual_revenue": application.annual_revenue,
            "net_income": application.net_income,
            "total_assets": application.total_assets,
            "total_liabilities": application.total_liabilities,
            "documents": application.documents or [],
        }

        db_service.save_application(application_data)

        return {
            "status": "success",
            "application_id": application_id,
            "message": "Application created successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=dict)
async def list_applications(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List all applications with optional filtering."""
    try:
        applications = db_service.list_applications(
            status=status,
            limit=limit,
            offset=offset
        )

        return {
            "status": "success",
            "applications": applications,
            "count": len(applications),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{application_id}", response_model=dict)
async def get_application(application_id: str):
    """Get a specific application by ID."""
    try:
        application = db_service.get_application(application_id)

        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {application_id} not found"
            )

        return {
            "status": "success",
            "application": application,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{application_id}/status", response_model=dict)
async def update_application_status(
    application_id: str,
    status: str,
    workflow_id: Optional[str] = None
):
    """Update the status of an application."""
    try:
        application = db_service.get_application(application_id)

        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {application_id} not found"
            )

        valid_statuses = [
            "pending", "processing", "under_review",
            "approved", "declined", "cancelled"
        ]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {valid_statuses}"
            )

        db_service.update_application_status(
            application_id=application_id,
            status=status,
            workflow_id=workflow_id
        )

        return {
            "status": "success",
            "message": f"Application status updated to {status}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{application_id}/history", response_model=dict)
async def get_application_history(application_id: str):
    """Get the history of an application including predictions and decisions."""
    try:
        application = db_service.get_application(application_id)

        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {application_id} not found"
            )

        decision = db_service.get_decision(application_id)

        return {
            "status": "success",
            "application": application,
            "decision": decision,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", response_model=dict)
async def get_application_stats():
    """Get summary statistics for applications."""
    try:
        all_apps = db_service.list_applications(limit=1000)

        stats = {
            "total": len(all_apps),
            "by_status": {},
        }

        for app in all_apps:
            status = app.get("status", "unknown")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        return {
            "status": "success",
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

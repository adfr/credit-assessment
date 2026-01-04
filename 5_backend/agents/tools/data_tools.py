"""
Data Tools
Tools for database operations and data retrieval.
"""

import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.iceberg_service import IcebergService

# Initialize service
_db_service = IcebergService()


def get_customer_history(company_id: str) -> dict:
    """
    Get historical data for a customer.

    Args:
        company_id: Unique company identifier

    Returns:
        Dictionary with company info, loan history, and bureau data
    """
    try:
        history = _db_service.get_customer_history(company_id)
        return {
            "status": "success",
            "company": history.get("company"),
            "loans": history.get("loans", []),
            "bureau": history.get("bureau"),
            "has_history": history.get("company") is not None,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "has_history": False,
        }


def get_industry_benchmarks(industry: str) -> dict:
    """
    Get industry benchmarks for comparison.

    Args:
        industry: Industry name/code

    Returns:
        Dictionary with industry metrics
    """
    try:
        benchmarks = _db_service.get_industry_benchmarks(industry)
        return {
            "status": "success",
            "industry": industry,
            "default_rate": benchmarks.get("default_rate", 0.05),
            "avg_revenue": benchmarks.get("avg_revenue", 50000000),
            "company_count": benchmarks.get("company_count", 0),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def save_application(application_data: dict) -> dict:
    """
    Save a new credit application.

    Args:
        application_data: Complete application data

    Returns:
        Dictionary with application_id and status
    """
    try:
        import uuid

        if "application_id" not in application_data:
            application_data["application_id"] = str(uuid.uuid4())

        app_id = _db_service.save_application(application_data)

        return {
            "status": "success",
            "application_id": app_id,
            "message": "Application saved successfully",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def get_application(application_id: str) -> dict:
    """
    Get application by ID.

    Args:
        application_id: Application identifier

    Returns:
        Dictionary with application data
    """
    try:
        app = _db_service.get_application(application_id)
        if app:
            return {
                "status": "success",
                "application": app,
            }
        return {
            "status": "not_found",
            "error": f"Application {application_id} not found",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def list_applications(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> dict:
    """
    List applications with optional filtering.

    Args:
        status: Filter by status (pending, approved, declined, etc.)
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        Dictionary with list of applications
    """
    try:
        apps = _db_service.list_applications(status=status, limit=limit, offset=offset)
        return {
            "status": "success",
            "applications": apps,
            "count": len(apps),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "applications": [],
        }


def update_application_status(
    application_id: str,
    status: str,
    workflow_id: Optional[str] = None
) -> dict:
    """
    Update application status.

    Args:
        application_id: Application identifier
        status: New status
        workflow_id: Associated workflow ID

    Returns:
        Dictionary with update result
    """
    try:
        _db_service.update_application_status(
            application_id=application_id,
            status=status,
            workflow_id=workflow_id
        )
        return {
            "status": "success",
            "message": f"Application status updated to {status}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def save_prediction(prediction_data: dict) -> dict:
    """
    Save model prediction for audit trail.

    Args:
        prediction_data: Prediction results and metadata

    Returns:
        Dictionary with save status
    """
    try:
        _db_service.save_prediction(prediction_data)
        return {
            "status": "success",
            "message": "Prediction saved for audit",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def save_decision(decision_data: dict) -> dict:
    """
    Save final decision.

    Args:
        decision_data: Decision details and metadata

    Returns:
        Dictionary with save status
    """
    try:
        _db_service.save_decision(decision_data)
        return {
            "status": "success",
            "message": "Decision recorded",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

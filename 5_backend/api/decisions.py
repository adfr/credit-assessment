"""
Decisions API Routes
Decision management and override endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from services.iceberg_service import IcebergService
from services.model_service import ModelService

router = APIRouter(prefix="/decisions", tags=["decisions"])

db_service = IcebergService()
model_service = ModelService()


class DecisionOverrideRequest(BaseModel):
    decision: str  # approve, decline
    reason: str
    approved_by: str
    approved_amount: Optional[float] = None
    approved_rate: Optional[float] = None
    approved_term_months: Optional[int] = None
    conditions: List[str] = []


class DecisionCreateRequest(BaseModel):
    application_id: str
    final_decision: str
    decision_type: str = "auto"
    decision_reason: Optional[str] = None
    approved_by: str = "system"
    approved_amount: Optional[float] = None
    approved_rate: Optional[float] = None
    approved_term_months: Optional[int] = None
    conditions: List[str] = []
    pd_at_decision: Optional[float] = None
    lgd_at_decision: Optional[float] = None
    el_at_decision: Optional[float] = None


@router.get("/{application_id}", response_model=dict)
async def get_decision(application_id: str):
    """Get the decision for an application."""
    try:
        decision = db_service.get_decision(application_id)

        if not decision:
            # Check if application exists
            application = db_service.get_application(application_id)
            if not application:
                raise HTTPException(
                    status_code=404,
                    detail=f"Application {application_id} not found"
                )

            return {
                "status": "success",
                "decision": None,
                "message": "No decision has been made yet",
            }

        return {
            "status": "success",
            "decision": decision,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=dict)
async def create_decision(request: DecisionCreateRequest):
    """Create a new decision for an application."""
    try:
        # Verify application exists
        application = db_service.get_application(request.application_id)
        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {request.application_id} not found"
            )

        # Check if decision already exists
        existing_decision = db_service.get_decision(request.application_id)
        if existing_decision:
            raise HTTPException(
                status_code=400,
                detail="Decision already exists for this application. Use override endpoint."
            )

        # Validate decision
        valid_decisions = ["APPROVE", "DECLINE", "REFER"]
        if request.final_decision.upper() not in valid_decisions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision. Must be one of: {valid_decisions}"
            )

        decision_data = {
            "application_id": request.application_id,
            "final_decision": request.final_decision.upper(),
            "decision_type": request.decision_type,
            "decision_reason": request.decision_reason,
            "approved_by": request.approved_by,
            "approved_amount": request.approved_amount,
            "approved_rate": request.approved_rate,
            "approved_term_months": request.approved_term_months,
            "conditions": request.conditions,
            "pd_at_decision": request.pd_at_decision,
            "lgd_at_decision": request.lgd_at_decision,
            "el_at_decision": request.el_at_decision,
        }

        db_service.save_decision(decision_data)

        # Update application status
        status_map = {
            "APPROVE": "approved",
            "DECLINE": "declined",
            "REFER": "under_review",
        }
        new_status = status_map.get(request.final_decision.upper(), "pending")
        db_service.update_application_status(request.application_id, new_status)

        return {
            "status": "success",
            "message": f"Decision recorded: {request.final_decision}",
            "application_id": request.application_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{application_id}/override", response_model=dict)
async def override_decision(
    application_id: str,
    request: DecisionOverrideRequest
):
    """Override an existing decision (requires authorization)."""
    try:
        # Verify application exists
        application = db_service.get_application(application_id)
        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {application_id} not found"
            )

        # Get existing decision
        existing_decision = db_service.get_decision(application_id)
        if not existing_decision:
            raise HTTPException(
                status_code=400,
                detail="No existing decision to override"
            )

        # Validate new decision
        valid_decisions = ["approve", "decline"]
        if request.decision.lower() not in valid_decisions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid decision. Must be one of: {valid_decisions}"
            )

        # Create override record (in production, would update existing)
        override_data = {
            "application_id": application_id,
            "final_decision": request.decision.upper(),
            "decision_type": "manual_override",
            "decision_reason": request.reason,
            "approved_by": request.approved_by,
            "approved_amount": request.approved_amount,
            "approved_rate": request.approved_rate,
            "approved_term_months": request.approved_term_months,
            "conditions": request.conditions,
            "pd_at_decision": existing_decision.get("pd_at_decision"),
            "lgd_at_decision": existing_decision.get("lgd_at_decision"),
            "el_at_decision": existing_decision.get("el_at_decision"),
            "previous_decision": existing_decision.get("final_decision"),
        }

        # In production, would update existing decision
        # For now, log the override
        db_service.save_decision(override_data)

        # Update application status
        new_status = "approved" if request.decision.lower() == "approve" else "declined"
        db_service.update_application_status(application_id, new_status)

        return {
            "status": "success",
            "message": f"Decision overridden to: {request.decision}",
            "override": {
                "previous_decision": existing_decision.get("final_decision"),
                "new_decision": request.decision.upper(),
                "overridden_by": request.approved_by,
                "reason": request.reason,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{application_id}/recommendation", response_model=dict)
async def get_decision_recommendation(application_id: str):
    """Get a decision recommendation based on risk scores."""
    try:
        application = db_service.get_application(application_id)
        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {application_id} not found"
            )

        # Get or calculate risk scores
        decision = db_service.get_decision(application_id)

        if decision:
            pd_score = decision.get("pd_at_decision", 0.05)
            rorac = 0.15  # Would calculate from risk engine
        else:
            # Use defaults for demo
            pd_score = 0.05
            rorac = 0.15

        # Get recommendation
        recommendation = await model_service.get_decision_recommendation(
            pd_score=pd_score,
            rorac=rorac,
            compliance_passed=True
        )

        # Get risk grade
        risk_grade = await model_service.get_risk_grade(pd_score)

        return {
            "status": "success",
            "application_id": application_id,
            "recommendation": recommendation,
            "risk_metrics": {
                "pd_score": pd_score,
                "rorac": rorac,
                "risk_grade": risk_grade,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", response_model=dict)
async def get_decision_stats():
    """Get summary statistics for decisions."""
    try:
        # Get all applications with decisions
        all_apps = db_service.list_applications(limit=1000)

        stats = {
            "total_decisions": 0,
            "by_outcome": {
                "approved": 0,
                "declined": 0,
                "referred": 0,
            },
            "by_type": {
                "auto": 0,
                "manual": 0,
                "override": 0,
            },
        }

        for app in all_apps:
            decision = db_service.get_decision(app.get("application_id"))
            if decision:
                stats["total_decisions"] += 1

                outcome = decision.get("final_decision", "").lower()
                if outcome in stats["by_outcome"]:
                    stats["by_outcome"][outcome] += 1

                decision_type = decision.get("decision_type", "auto")
                if "override" in decision_type:
                    stats["by_type"]["override"] += 1
                elif decision_type == "manual":
                    stats["by_type"]["manual"] += 1
                else:
                    stats["by_type"]["auto"] += 1

        return {
            "status": "success",
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

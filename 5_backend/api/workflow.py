"""
Workflow API Routes
Workflow management and execution endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel
import uuid
from datetime import datetime

from agents.graph import create_workflow_graph
from services.iceberg_service import IcebergService

router = APIRouter(prefix="/workflow", tags=["workflow"])

db_service = IcebergService()

# In-memory workflow state store (use Redis in production)
workflow_states: Dict[str, Dict[str, Any]] = {}


class WorkflowStartRequest(BaseModel):
    application_id: str
    auto_approve: bool = True


class WorkflowResumeRequest(BaseModel):
    workflow_id: str
    decision: str
    notes: Optional[str] = None


@router.post("/start", response_model=dict)
async def start_workflow(
    request: WorkflowStartRequest,
    background_tasks: BackgroundTasks
):
    """Start a new workflow for an application."""
    try:
        # Verify application exists
        application = db_service.get_application(request.application_id)
        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {request.application_id} not found"
            )

        workflow_id = str(uuid.uuid4())

        # Initialize workflow state
        initial_state = {
            "application_id": request.application_id,
            "workflow_id": workflow_id,
            "status": "started",
            "current_step": "document_processing",
            "started_at": datetime.now().isoformat(),
            "steps_completed": [],
            "auto_approve": request.auto_approve,
        }

        workflow_states[workflow_id] = initial_state

        # Update application status
        db_service.update_application_status(
            application_id=request.application_id,
            status="processing",
            workflow_id=workflow_id
        )

        # Run workflow in background
        background_tasks.add_task(
            run_workflow,
            workflow_id,
            request.application_id,
            application
        )

        return {
            "status": "success",
            "workflow_id": workflow_id,
            "message": "Workflow started",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_workflow(
    workflow_id: str,
    application_id: str,
    application_data: dict
):
    """Execute the workflow graph."""
    try:
        graph = create_workflow_graph()

        # Prepare initial state
        state = {
            "application_id": application_id,
            "workflow_id": workflow_id,
            "application_data": application_data,
            "documents": [],
            "validation_results": {},
            "enrichment_data": {},
            "compliance_checks": {},
            "risk_scores": {},
            "review_status": "pending",
            "decision": None,
            "conditions": [],
            "current_step": "document_processing",
            "step_outputs": {},
            "errors": [],
        }

        # Run the graph
        config = {"configurable": {"thread_id": workflow_id}}
        final_state = await graph.ainvoke(state, config)

        # Update workflow state
        workflow_states[workflow_id].update({
            "status": "completed",
            "final_state": final_state,
            "completed_at": datetime.now().isoformat(),
        })

        # Update application status based on decision
        decision = final_state.get("decision", {})
        if decision.get("final_decision") == "APPROVE":
            db_service.update_application_status(application_id, "approved")
        elif decision.get("final_decision") == "DECLINE":
            db_service.update_application_status(application_id, "declined")
        else:
            db_service.update_application_status(application_id, "under_review")

    except Exception as e:
        workflow_states[workflow_id].update({
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat(),
        })


@router.get("/{workflow_id}", response_model=dict)
async def get_workflow_status(workflow_id: str):
    """Get the current status of a workflow."""
    if workflow_id not in workflow_states:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {workflow_id} not found"
        )

    return {
        "status": "success",
        "workflow": workflow_states[workflow_id],
    }


@router.get("/{workflow_id}/steps", response_model=dict)
async def get_workflow_steps(workflow_id: str):
    """Get detailed step information for a workflow."""
    if workflow_id not in workflow_states:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {workflow_id} not found"
        )

    workflow = workflow_states[workflow_id]

    steps = [
        {"name": "document_processing", "label": "Document Processing"},
        {"name": "validation", "label": "Validation"},
        {"name": "enrichment", "label": "Data Enrichment"},
        {"name": "compliance", "label": "Compliance Check"},
        {"name": "scoring", "label": "Risk Scoring"},
        {"name": "review", "label": "Human Review"},
        {"name": "decision", "label": "Decision"},
    ]

    current_step = workflow.get("current_step")
    completed_steps = workflow.get("steps_completed", [])

    for step in steps:
        if step["name"] in completed_steps:
            step["status"] = "completed"
        elif step["name"] == current_step:
            step["status"] = "in_progress"
        else:
            step["status"] = "pending"

    return {
        "status": "success",
        "workflow_id": workflow_id,
        "steps": steps,
        "current_step": current_step,
    }


@router.post("/{workflow_id}/resume", response_model=dict)
async def resume_workflow(
    workflow_id: str,
    request: WorkflowResumeRequest,
    background_tasks: BackgroundTasks
):
    """Resume a paused workflow with human decision."""
    if workflow_id not in workflow_states:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {workflow_id} not found"
        )

    workflow = workflow_states[workflow_id]

    if workflow.get("status") != "paused":
        raise HTTPException(
            status_code=400,
            detail="Workflow is not paused"
        )

    # Update with human decision
    workflow["human_decision"] = {
        "decision": request.decision,
        "notes": request.notes,
        "timestamp": datetime.now().isoformat(),
    }
    workflow["status"] = "resuming"

    return {
        "status": "success",
        "message": "Workflow resumed with decision",
    }


@router.post("/{workflow_id}/cancel", response_model=dict)
async def cancel_workflow(workflow_id: str):
    """Cancel a running workflow."""
    if workflow_id not in workflow_states:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow {workflow_id} not found"
        )

    workflow = workflow_states[workflow_id]

    if workflow.get("status") in ["completed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail="Workflow cannot be cancelled"
        )

    workflow["status"] = "cancelled"
    workflow["cancelled_at"] = datetime.now().isoformat()

    # Update application status
    application_id = workflow.get("application_id")
    if application_id:
        db_service.update_application_status(application_id, "cancelled")

    return {
        "status": "success",
        "message": "Workflow cancelled",
    }


@router.get("/", response_model=dict)
async def list_workflows(
    status: Optional[str] = None,
    limit: int = 50
):
    """List all workflows with optional filtering."""
    workflows = list(workflow_states.values())

    if status:
        workflows = [w for w in workflows if w.get("status") == status]

    workflows = sorted(
        workflows,
        key=lambda x: x.get("started_at", ""),
        reverse=True
    )[:limit]

    return {
        "status": "success",
        "workflows": workflows,
        "count": len(workflows),
    }

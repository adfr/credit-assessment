"""
Credit Risk Platform - FastAPI Application
Main entry point for the backend API.
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from models import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatus,
    WorkflowStartRequest,
    WorkflowStartResponse,
    WorkflowStatus,
    RiskDecision,
)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("[INFO] Starting Credit Risk Platform API...")
    print(f"[INFO] API running on {settings.api_host}:{settings.api_port}")
    yield
    print("[INFO] Shutting down Credit Risk Platform API...")


# Create FastAPI app
app = FastAPI(
    title="Credit Risk Platform API",
    description="API for credit risk assessment and approval workflow",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory storage (replace with database in production)
applications_db = {}
workflows_db = {}
websocket_connections = {}


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }


# ============================================================================
# Application Endpoints
# ============================================================================

@app.post("/api/applications", response_model=dict)
async def create_application(application: ApplicationCreate):
    """Create a new credit application."""
    application_id = f"APP-{uuid.uuid4().hex[:8].upper()}"

    app_data = {
        "application_id": application_id,
        "status": ApplicationStatus.PENDING,
        "customer": application.customer.model_dump(),
        "loan": application.loan.model_dump(),
        "documents": [doc.model_dump() for doc in application.documents] if application.documents else [],
        "submitted_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "workflow_id": None,
    }

    applications_db[application_id] = app_data

    return {
        "application_id": application_id,
        "status": "pending",
        "message": "Application created successfully",
    }


@app.get("/api/applications")
async def list_applications(
    status: str = None,
    page: int = 1,
    page_size: int = 20,
):
    """List all applications with optional filtering."""
    apps = list(applications_db.values())

    if status:
        apps = [a for a in apps if a["status"] == status]

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated = apps[start:end]

    return {
        "applications": paginated,
        "total": len(apps),
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/applications/{application_id}")
async def get_application(application_id: str):
    """Get application details."""
    if application_id not in applications_db:
        raise HTTPException(status_code=404, detail="Application not found")

    return applications_db[application_id]


# ============================================================================
# Workflow Endpoints
# ============================================================================

@app.post("/api/workflow/start")
async def start_workflow(request: WorkflowStartRequest):
    """Start workflow for an application."""
    application_id = request.application_id

    if application_id not in applications_db:
        raise HTTPException(status_code=404, detail="Application not found")

    app_data = applications_db[application_id]

    # Create workflow
    workflow_id = f"WF-{uuid.uuid4().hex[:8].upper()}"

    try:
        from agents.graph import run_workflow

        # Run workflow
        result = await run_workflow(
            application_id=application_id,
            workflow_id=workflow_id,
            customer_data=app_data["customer"],
            loan_request=app_data["loan"],
            documents=app_data.get("documents", []),
        )

        # Store workflow state
        workflows_db[workflow_id] = {
            "workflow_id": workflow_id,
            "application_id": application_id,
            "status": WorkflowStatus.RUNNING,
            "current_step": result.get("current_step", "unknown") if result else "unknown",
            "state": result,
            "started_at": datetime.now().isoformat(),
        }

        # Update application
        app_data["workflow_id"] = workflow_id
        app_data["status"] = ApplicationStatus.IN_PROGRESS

        return {
            "workflow_id": workflow_id,
            "application_id": application_id,
            "status": "running",
            "current_step": workflows_db[workflow_id]["current_step"],
            "message": "Workflow started successfully",
        }

    except Exception as e:
        return {
            "workflow_id": None,
            "application_id": application_id,
            "status": "error",
            "error": str(e),
        }


@app.get("/api/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get current workflow status."""
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")

    wf = workflows_db[workflow_id]
    state = wf.get("state", {})

    return {
        "workflow_id": workflow_id,
        "application_id": wf["application_id"],
        "status": wf["status"],
        "current_step": state.get("current_step", "unknown"),
        "risk_scores": state.get("risk_scores", {}),
        "final_decision": state.get("final_decision"),
    }


@app.post("/api/workflow/{workflow_id}/resume")
async def resume_workflow(workflow_id: str, decision: str, notes: str = None):
    """Resume workflow after human review."""
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")

    try:
        from agents.graph import resume_workflow as resume_wf

        result = await resume_wf(
            workflow_id=workflow_id,
            human_decision=decision,
            analyst_notes=notes,
        )

        workflows_db[workflow_id]["state"] = result
        workflows_db[workflow_id]["current_step"] = result.get("current_step", "unknown") if result else "unknown"

        return {
            "workflow_id": workflow_id,
            "status": "resumed",
            "current_step": workflows_db[workflow_id]["current_step"],
        }

    except Exception as e:
        return {
            "workflow_id": workflow_id,
            "status": "error",
            "error": str(e),
        }


# ============================================================================
# Analyst Endpoints
# ============================================================================

class ChatRequest(BaseModel):
    application_id: str
    message: str


@app.post("/api/analyst/chat")
async def analyst_chat(request: ChatRequest):
    """AI analyst chat endpoint."""
    # Import RAG service
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "4_endpoints"))
        from serve_rag import query

        # Get application context
        app_data = applications_db.get(request.application_id, {})

        result = query({
            "question": request.message,
            "customer_id": request.application_id,
            "risk_context": app_data.get("risk_scores"),
        })

        return {
            "application_id": request.application_id,
            "question": request.message,
            "answer": result.get("answer", "Unable to generate response"),
            "sources": result.get("sources", []),
        }

    except Exception as e:
        return {
            "application_id": request.application_id,
            "question": request.message,
            "answer": f"Error: {str(e)}",
            "sources": [],
        }


# ============================================================================
# Decision Endpoints
# ============================================================================

@app.get("/api/decisions/{application_id}")
async def get_decision(application_id: str):
    """Get final decision for an application."""
    if application_id not in applications_db:
        raise HTTPException(status_code=404, detail="Application not found")

    app_data = applications_db[application_id]
    workflow_id = app_data.get("workflow_id")

    if not workflow_id or workflow_id not in workflows_db:
        return {
            "application_id": application_id,
            "decision": None,
            "message": "No decision yet",
        }

    state = workflows_db[workflow_id].get("state", {})

    return {
        "application_id": application_id,
        "decision": state.get("final_decision"),
        "decision_reason": state.get("decision_reason"),
        "conditions": state.get("decision_conditions", []),
        "risk_grade": state.get("risk_grade"),
        "pd_score": state.get("pd_score"),
        "lgd_score": state.get("lgd_score"),
    }


# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================

@app.websocket("/ws/workflow/{application_id}")
async def workflow_websocket(websocket: WebSocket, application_id: str):
    """WebSocket for real-time workflow updates."""
    await websocket.accept()
    websocket_connections[application_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            await websocket.send_json({
                "type": "ack",
                "message": f"Received: {data}",
            })
    except WebSocketDisconnect:
        if application_id in websocket_connections:
            del websocket_connections[application_id]


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )

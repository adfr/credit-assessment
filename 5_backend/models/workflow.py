"""
Workflow Pydantic Models
Data models for LangGraph workflow state and steps.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Individual step status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class WorkflowStep(BaseModel):
    """Individual workflow step information."""
    step_name: str
    status: StepStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class StepResult(BaseModel):
    """Result from a workflow step execution."""
    step_name: str
    success: bool
    data: dict = {}
    messages: list[str] = []
    next_step: Optional[str] = None


class WorkflowState(BaseModel):
    """Complete workflow state representation."""
    workflow_id: str
    application_id: str

    # Current status
    status: WorkflowStatus
    current_step: Optional[str] = None

    # Step history
    steps: list[WorkflowStep] = []
    step_count: int = 0

    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    # Error tracking
    error: Optional[str] = None
    retry_count: int = 0


class WorkflowStartRequest(BaseModel):
    """Request to start a workflow."""
    application_id: str


class WorkflowStartResponse(BaseModel):
    """Response after starting a workflow."""
    workflow_id: str
    application_id: str
    status: WorkflowStatus
    current_step: str
    message: str


class WorkflowResumeRequest(BaseModel):
    """Request to resume a paused workflow."""
    human_decision: str = Field(..., description="APPROVE, DECLINE, or REQUEST_INFO")
    analyst_notes: Optional[str] = None
    conditions: Optional[list[str]] = None


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status query."""
    workflow_id: str
    application_id: str
    status: WorkflowStatus
    current_step: Optional[str]
    progress_percentage: float
    steps_completed: int
    steps_total: int
    estimated_time_remaining: Optional[str] = None


class WorkflowHistoryResponse(BaseModel):
    """Response for workflow history."""
    workflow_id: str
    application_id: str
    status: WorkflowStatus
    steps: list[WorkflowStep]
    total_duration_seconds: Optional[float] = None

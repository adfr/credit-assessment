"""
Decision Pydantic Models
Data models for credit decisions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from .risk import RiskDecision, RiskGrade


class DecisionType(str, Enum):
    """Type of decision."""
    AUTO = "auto"
    MANUAL = "manual"
    OVERRIDE = "override"


class DecisionCondition(BaseModel):
    """Condition attached to approval."""
    condition_id: str
    description: str
    condition_type: str  # documentation, financial_covenant, collateral, etc.
    due_date: Optional[datetime] = None
    required: bool = True


class DecisionResponse(BaseModel):
    """Complete decision response."""
    application_id: str
    decision: RiskDecision
    decision_type: DecisionType
    decision_reason: str

    # Approved terms (if approved)
    approved_amount: Optional[float] = None
    approved_rate: Optional[float] = None
    approved_term_months: Optional[int] = None

    # Conditions
    conditions: list[DecisionCondition] = []

    # Risk metrics at decision
    risk_grade: RiskGrade
    pd_at_decision: float
    lgd_at_decision: float
    el_at_decision: float

    # Audit trail
    decided_by: str  # system, analyst_id
    decided_at: datetime
    notes: Optional[str] = None


class DecisionOverrideRequest(BaseModel):
    """Request to override a decision."""
    new_decision: RiskDecision
    override_reason: str = Field(..., min_length=10)
    approved_amount: Optional[float] = None
    approved_rate: Optional[float] = None
    approved_term_months: Optional[int] = None
    conditions: list[str] = []
    authorization_code: Optional[str] = None


class AnalystNote(BaseModel):
    """Analyst note for an application."""
    note_id: str
    application_id: str
    analyst_id: str
    note_text: str
    note_type: str = "general"  # general, concern, recommendation
    created_at: datetime


class DecisionSummary(BaseModel):
    """Summary for decision reporting."""
    application_id: str
    company_name: str
    requested_amount: float
    decision: RiskDecision
    risk_grade: RiskGrade
    decided_at: datetime
    decision_type: DecisionType

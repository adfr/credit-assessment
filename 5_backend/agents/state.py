"""
LangGraph State Definition
Defines the state schema for the credit workflow.
"""

from typing import TypedDict, Annotated, Optional, Sequence
from datetime import datetime
import operator


class CreditWorkflowState(TypedDict):
    """
    Complete state for the credit approval workflow.
    This state is passed through all nodes and updated as the workflow progresses.
    """

    # Application identifiers
    application_id: str
    workflow_id: str

    # Customer and loan data
    customer_data: dict
    loan_request: dict

    # Document processing
    documents: list[dict]
    extracted_data: dict

    # Validation results
    validation_results: dict
    validation_passed: bool

    # Bureau data
    bureau_data: dict
    bureau_score: Optional[float]

    # Risk scoring
    risk_scores: dict
    pd_score: Optional[float]
    lgd_score: Optional[float]
    expected_loss: Optional[float]
    rorac: Optional[float]
    risk_grade: Optional[str]

    # Compliance
    compliance_flags: list[str]
    compliance_passed: bool

    # Decision routing
    initial_decision: Optional[str]  # APPROVE, REFER, DECLINE
    requires_review: bool

    # Human review
    analyst_notes: Annotated[list[str], operator.add]
    human_decision: Optional[str]
    review_completed: bool

    # Final decision
    final_decision: Optional[str]
    decision_conditions: list[str]
    decision_reason: Optional[str]

    # Workflow tracking
    current_step: str
    step_history: Annotated[list[dict], operator.add]
    error: Optional[str]

    # Messages (for chat in review step)
    messages: Annotated[Sequence[dict], operator.add]

    # Timestamps
    started_at: Optional[str]
    updated_at: Optional[str]
    completed_at: Optional[str]


def create_initial_state(
    application_id: str,
    workflow_id: str,
    customer_data: dict,
    loan_request: dict,
    documents: list[dict] = None
) -> CreditWorkflowState:
    """Create initial workflow state."""
    return CreditWorkflowState(
        # Identifiers
        application_id=application_id,
        workflow_id=workflow_id,

        # Input data
        customer_data=customer_data,
        loan_request=loan_request,
        documents=documents or [],
        extracted_data={},

        # Validation
        validation_results={},
        validation_passed=False,

        # Bureau
        bureau_data={},
        bureau_score=None,

        # Risk
        risk_scores={},
        pd_score=None,
        lgd_score=None,
        expected_loss=None,
        rorac=None,
        risk_grade=None,

        # Compliance
        compliance_flags=[],
        compliance_passed=False,

        # Decision routing
        initial_decision=None,
        requires_review=True,

        # Review
        analyst_notes=[],
        human_decision=None,
        review_completed=False,

        # Final
        final_decision=None,
        decision_conditions=[],
        decision_reason=None,

        # Tracking
        current_step="start",
        step_history=[],
        error=None,
        messages=[],

        # Timestamps
        started_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        completed_at=None,
    )


def update_step(state: CreditWorkflowState, step_name: str, result: dict = None) -> dict:
    """Create a step history entry."""
    return {
        "step": step_name,
        "timestamp": datetime.now().isoformat(),
        "result": result or {},
    }

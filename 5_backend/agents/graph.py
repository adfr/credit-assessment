"""
Main LangGraph Workflow
Defines the credit approval workflow graph.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import CreditWorkflowState, create_initial_state
from .nodes import (
    document_node,
    validation_node,
    enrichment_node,
    compliance_node,
    scoring_node,
    review_node,
    decision_node,
)


def route_after_compliance(state: CreditWorkflowState) -> Literal["scoring", "decision"]:
    """Route after compliance check."""
    if state.get("compliance_passed", False):
        return "scoring"
    else:
        return "decision"


def route_after_scoring(state: CreditWorkflowState) -> Literal["review", "decision"]:
    """Route after scoring based on initial decision."""
    initial_decision = state.get("initial_decision")

    if initial_decision == "REFER":
        return "review"
    else:
        # AUTO_APPROVE or AUTO_DECLINE
        return "decision"


def route_after_review(state: CreditWorkflowState) -> Literal["document", "decision"]:
    """Route after human review."""
    human_decision = state.get("human_decision")

    if human_decision == "REQUEST_INFO":
        # Loop back to document collection
        return "document"
    else:
        return "decision"


def build_workflow() -> StateGraph:
    """Build the credit approval workflow graph."""

    # Create the graph
    workflow = StateGraph(CreditWorkflowState)

    # Add nodes
    workflow.add_node("document", document_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("enrichment", enrichment_node)
    workflow.add_node("compliance", compliance_node)
    workflow.add_node("scoring", scoring_node)
    workflow.add_node("review", review_node)
    workflow.add_node("decision", decision_node)

    # Add edges
    workflow.add_edge("document", "validation")
    workflow.add_edge("validation", "enrichment")
    workflow.add_edge("enrichment", "compliance")

    # Conditional edges after compliance
    workflow.add_conditional_edges(
        "compliance",
        route_after_compliance,
        {
            "scoring": "scoring",
            "decision": "decision",
        }
    )

    # Conditional edges after scoring
    workflow.add_conditional_edges(
        "scoring",
        route_after_scoring,
        {
            "review": "review",
            "decision": "decision",
        }
    )

    # Review is an interrupt point - manual edge to decision after resume
    workflow.add_edge("review", "decision")

    # Decision is the end
    workflow.add_edge("decision", END)

    # Set entry point
    workflow.set_entry_point("document")

    return workflow


def create_workflow_app(checkpointer=None):
    """Create a compiled workflow application."""

    workflow = build_workflow()

    if checkpointer is None:
        # Use in-memory checkpointer for development
        checkpointer = MemorySaver()

    # Compile with checkpointer and interrupt points
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["review"],  # Pause before human review
    )

    return app


# Create default workflow app
_default_app = None


def get_workflow_app():
    """Get or create the default workflow app."""
    global _default_app
    if _default_app is None:
        _default_app = create_workflow_app()
    return _default_app


async def run_workflow(
    application_id: str,
    workflow_id: str,
    customer_data: dict,
    loan_request: dict,
    documents: list = None,
) -> dict:
    """Run the workflow for an application."""

    app = get_workflow_app()

    # Create initial state
    initial_state = create_initial_state(
        application_id=application_id,
        workflow_id=workflow_id,
        customer_data=customer_data,
        loan_request=loan_request,
        documents=documents or [],
    )

    # Configure the run
    config = {
        "configurable": {
            "thread_id": workflow_id,
        }
    }

    # Run the workflow
    result = None
    async for event in app.astream(initial_state, config):
        result = event

    return result


async def resume_workflow(
    workflow_id: str,
    human_decision: str,
    analyst_notes: str = None,
) -> dict:
    """Resume a paused workflow after human review."""

    app = get_workflow_app()

    config = {
        "configurable": {
            "thread_id": workflow_id,
        }
    }

    # Update state with human decision
    update = {
        "human_decision": human_decision,
        "review_completed": True,
    }

    if analyst_notes:
        update["analyst_notes"] = [analyst_notes]

    # Resume the workflow
    result = None
    async for event in app.astream(update, config):
        result = event

    return result


def get_workflow_state(workflow_id: str) -> dict:
    """Get current state of a workflow."""
    app = get_workflow_app()

    config = {
        "configurable": {
            "thread_id": workflow_id,
        }
    }

    state = app.get_state(config)
    return state.values if state else None

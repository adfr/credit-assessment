"""
LangGraph Node Functions
Each node represents a step in the credit approval workflow.
"""

from datetime import datetime
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.state import CreditWorkflowState, update_step


def document_node(state: CreditWorkflowState) -> Dict[str, Any]:
    """
    Process uploaded documents and extract structured data.
    """
    print(f"[DOCUMENT_NODE] Processing documents for {state['application_id']}")

    documents = state.get("documents", [])
    extracted_data = {}

    # Simulate document extraction
    for doc in documents:
        doc_type = doc.get("document_type", "unknown")
        if doc_type == "financial_statement":
            extracted_data["financials_extracted"] = True
        elif doc_type == "loan_application":
            extracted_data["application_extracted"] = True

    # If no documents, use customer_data as extracted
    if not documents:
        extracted_data = state.get("customer_data", {})

    return {
        "extracted_data": extracted_data,
        "current_step": "validation",
        "step_history": [update_step(state, "document_processing", {"documents_processed": len(documents)})],
        "updated_at": datetime.now().isoformat(),
    }


def validation_node(state: CreditWorkflowState) -> Dict[str, Any]:
    """
    Validate extracted data and check required fields.
    """
    print(f"[VALIDATION_NODE] Validating data for {state['application_id']}")

    customer_data = state.get("customer_data", {})
    loan_request = state.get("loan_request", {})

    validation_results = {
        "required_fields": True,
        "data_consistency": True,
        "amount_within_limits": True,
        "issues": [],
    }

    # Check required customer fields
    required_customer = ["company_name", "annual_revenue", "total_assets"]
    for field in required_customer:
        if not customer_data.get(field):
            validation_results["required_fields"] = False
            validation_results["issues"].append(f"Missing: {field}")

    # Check loan amount limits
    requested_amount = loan_request.get("requested_amount", 0)
    if requested_amount < 100000 or requested_amount > 50000000:
        validation_results["amount_within_limits"] = False
        validation_results["issues"].append("Amount outside limits")

    validation_passed = all([
        validation_results["required_fields"],
        validation_results["data_consistency"],
        validation_results["amount_within_limits"],
    ])

    return {
        "validation_results": validation_results,
        "validation_passed": validation_passed,
        "current_step": "enrichment",
        "step_history": [update_step(state, "validation", {"passed": validation_passed})],
        "updated_at": datetime.now().isoformat(),
    }


def enrichment_node(state: CreditWorkflowState) -> Dict[str, Any]:
    """
    Enrich data with bureau information and industry benchmarks.
    """
    print(f"[ENRICHMENT_NODE] Enriching data for {state['application_id']}")

    customer_data = state.get("customer_data", {})

    # Simulate bureau data pull
    bureau_data = {
        "credit_score": 75,  # Business credit score
        "payment_index": 85,
        "derogatory_count": 0,
        "years_on_file": customer_data.get("years_in_business", 5),
        "trade_lines_count": 15,
        "utilization_rate": 0.45,
    }

    # Add industry benchmarks
    industry = customer_data.get("industry", "other")
    bureau_data["industry_default_rate"] = 0.04
    bureau_data["industry_risk_tier"] = 3

    return {
        "bureau_data": bureau_data,
        "bureau_score": bureau_data["credit_score"],
        "current_step": "compliance",
        "step_history": [update_step(state, "enrichment", {"bureau_score": bureau_data["credit_score"]})],
        "updated_at": datetime.now().isoformat(),
    }


def compliance_node(state: CreditWorkflowState) -> Dict[str, Any]:
    """
    Run compliance checks (sanctions, AML, policy rules).
    """
    print(f"[COMPLIANCE_NODE] Running compliance checks for {state['application_id']}")

    compliance_flags = []

    # Simulate compliance checks
    customer_data = state.get("customer_data", {})
    company_name = customer_data.get("company_name", "")

    # Sanctions check (simulated)
    sanctions_clear = True

    # AML check (simulated)
    aml_clear = True

    # Industry restrictions
    industry = customer_data.get("industry", "").lower()
    restricted_industries = ["gambling", "weapons", "tobacco"]
    industry_allowed = industry not in restricted_industries

    if not industry_allowed:
        compliance_flags.append(f"Restricted industry: {industry}")

    compliance_passed = sanctions_clear and aml_clear and industry_allowed

    return {
        "compliance_flags": compliance_flags,
        "compliance_passed": compliance_passed,
        "current_step": "scoring" if compliance_passed else "decision",
        "step_history": [update_step(state, "compliance", {"passed": compliance_passed})],
        "updated_at": datetime.now().isoformat(),
    }


def scoring_node(state: CreditWorkflowState) -> Dict[str, Any]:
    """
    Run risk scoring models (PD, LGD, calculate metrics).
    """
    print(f"[SCORING_NODE] Running risk models for {state['application_id']}")

    customer_data = state.get("customer_data", {})
    loan_request = state.get("loan_request", {})
    bureau_data = state.get("bureau_data", {})

    # Calculate basic features
    debt_to_equity = customer_data.get("total_liabilities", 1) / max(
        customer_data.get("total_assets", 1) - customer_data.get("total_liabilities", 0), 1
    )

    # Simulate PD calculation
    base_pd = 0.03
    if debt_to_equity > 2:
        base_pd += 0.02
    if bureau_data.get("credit_score", 70) < 60:
        base_pd += 0.03
    if bureau_data.get("derogatory_count", 0) > 0:
        base_pd += 0.01

    pd_score = min(base_pd, 0.50)

    # LGD based on collateral
    collateral_type = loan_request.get("collateral_type", "unsecured")
    lgd_map = {
        "real_estate": 0.35,
        "equipment": 0.45,
        "unsecured": 0.75,
    }
    lgd_score = lgd_map.get(collateral_type, 0.55)

    # Calculate metrics
    loan_amount = loan_request.get("requested_amount", 1000000)
    expected_loss = pd_score * lgd_score * loan_amount
    economic_capital = expected_loss * 2.5

    # RORAC
    interest_rate = loan_request.get("proposed_interest_rate", 0.06)
    annual_income = loan_amount * interest_rate
    rorac = (annual_income - expected_loss) / max(economic_capital, 1)

    # Risk grade
    if pd_score < 0.01:
        risk_grade = "A"
    elif pd_score < 0.03:
        risk_grade = "BBB"
    elif pd_score < 0.05:
        risk_grade = "BB"
    elif pd_score < 0.10:
        risk_grade = "B"
    else:
        risk_grade = "CCC"

    # Initial decision
    if pd_score < 0.03 and rorac > 0.12:
        initial_decision = "APPROVE"
        requires_review = False
    elif pd_score > 0.15:
        initial_decision = "DECLINE"
        requires_review = False
    else:
        initial_decision = "REFER"
        requires_review = True

    risk_scores = {
        "pd_score": pd_score,
        "lgd_score": lgd_score,
        "expected_loss": expected_loss,
        "economic_capital": economic_capital,
        "rorac": rorac,
        "risk_grade": risk_grade,
    }

    return {
        "risk_scores": risk_scores,
        "pd_score": pd_score,
        "lgd_score": lgd_score,
        "expected_loss": expected_loss,
        "rorac": rorac,
        "risk_grade": risk_grade,
        "initial_decision": initial_decision,
        "requires_review": requires_review,
        "current_step": "review" if requires_review else "decision",
        "step_history": [update_step(state, "scoring", {"pd": pd_score, "decision": initial_decision})],
        "updated_at": datetime.now().isoformat(),
    }


def review_node(state: CreditWorkflowState) -> Dict[str, Any]:
    """
    Human review checkpoint - workflow pauses here.
    """
    print(f"[REVIEW_NODE] Awaiting human review for {state['application_id']}")

    # This node signals the workflow should pause for human input
    return {
        "current_step": "review_pending",
        "step_history": [update_step(state, "review", {"status": "awaiting_human"})],
        "updated_at": datetime.now().isoformat(),
    }


def decision_node(state: CreditWorkflowState) -> Dict[str, Any]:
    """
    Generate final decision and conditions.
    """
    print(f"[DECISION_NODE] Generating decision for {state['application_id']}")

    # Determine final decision
    if not state.get("compliance_passed"):
        final_decision = "DECLINE"
        decision_reason = "Failed compliance checks"
    elif state.get("human_decision"):
        final_decision = state["human_decision"]
        decision_reason = "Analyst decision"
    else:
        final_decision = state.get("initial_decision", "REFER")
        decision_reason = "Model-based decision"

    # Set conditions for approvals
    conditions = []
    if final_decision == "APPROVE":
        pd_score = state.get("pd_score", 0)
        if pd_score > 0.05:
            conditions.append("Annual financial review required")
        if state.get("loan_request", {}).get("collateral_type") == "unsecured":
            conditions.append("Personal guarantee required")

    return {
        "final_decision": final_decision,
        "decision_reason": decision_reason,
        "decision_conditions": conditions,
        "current_step": "completed",
        "step_history": [update_step(state, "decision", {"decision": final_decision})],
        "completed_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


# Export all nodes
__all__ = [
    "document_node",
    "validation_node",
    "enrichment_node",
    "compliance_node",
    "scoring_node",
    "review_node",
    "decision_node",
]

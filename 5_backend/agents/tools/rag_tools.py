"""
RAG Tools
Tools for querying policy documents and knowledge base.
"""

import sys
from pathlib import Path
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "4_endpoints"))


def query_policies(question: str, n_results: int = 5) -> dict:
    """
    Query policy documents using RAG.

    Args:
        question: Natural language question about policies
        n_results: Number of relevant documents to retrieve

    Returns:
        Dictionary with answer and source documents
    """
    try:
        from serve_rag import query

        result = query({
            "question": question,
            "n_results": n_results,
        })

        return {
            "status": "success",
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", 0.0),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "answer": "Unable to retrieve policy information.",
        }


def query_documents(
    question: str,
    customer_id: Optional[str] = None,
    risk_context: Optional[dict] = None,
    n_results: int = 5
) -> dict:
    """
    Query documents with application context.

    Args:
        question: Natural language question
        customer_id: Optional customer/application ID for context
        risk_context: Optional risk scores and metrics for context
        n_results: Number of results to retrieve

    Returns:
        Dictionary with contextual answer and sources
    """
    try:
        from serve_rag import query

        args = {
            "question": question,
            "n_results": n_results,
        }

        if customer_id:
            args["customer_id"] = customer_id
        if risk_context:
            args["risk_context"] = risk_context

        result = query(args)

        return {
            "status": "success",
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "context_used": bool(customer_id or risk_context),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def get_policy_guidance(
    risk_grade: str,
    decision_type: str,
    amount: float
) -> dict:
    """
    Get specific policy guidance for a decision scenario.

    Args:
        risk_grade: Risk grade (AAA, AA, A, BBB, BB, B, CCC, CC, C, D)
        decision_type: Type of decision (approval, decline, referral)
        amount: Loan amount

    Returns:
        Dictionary with applicable policies and requirements
    """
    try:
        from serve_rag import query

        question = f"""What are the policy requirements for:
        - Risk Grade: {risk_grade}
        - Decision Type: {decision_type}
        - Loan Amount: ${amount:,.2f}

        Include approval authority limits, documentation requirements, and any special conditions."""

        result = query({
            "question": question,
            "n_results": 5,
        })

        return {
            "status": "success",
            "guidance": result.get("answer", ""),
            "policies": result.get("sources", []),
            "risk_grade": risk_grade,
            "decision_type": decision_type,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def get_compliance_requirements(
    industry: str,
    loan_type: str,
    jurisdiction: str = "US"
) -> dict:
    """
    Get compliance requirements for a specific scenario.

    Args:
        industry: Industry sector
        loan_type: Type of loan product
        jurisdiction: Geographic jurisdiction

    Returns:
        Dictionary with compliance requirements
    """
    try:
        from serve_rag import query

        question = f"""What are the compliance requirements for:
        - Industry: {industry}
        - Loan Type: {loan_type}
        - Jurisdiction: {jurisdiction}

        Include regulatory requirements, documentation needs, and any restricted activities."""

        result = query({
            "question": question,
            "n_results": 5,
        })

        return {
            "status": "success",
            "requirements": result.get("answer", ""),
            "sources": result.get("sources", []),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def search_similar_cases(
    industry: str,
    amount_range: tuple,
    risk_grade: str,
    n_results: int = 3
) -> dict:
    """
    Search for similar historical cases for reference.

    Args:
        industry: Industry sector
        amount_range: (min_amount, max_amount) tuple
        risk_grade: Risk grade
        n_results: Number of similar cases to return

    Returns:
        Dictionary with similar case references
    """
    try:
        from serve_rag import query

        min_amt, max_amt = amount_range
        question = f"""Find similar credit decisions for:
        - Industry: {industry}
        - Amount Range: ${min_amt:,.0f} - ${max_amt:,.0f}
        - Risk Grade: {risk_grade}

        What were the outcomes and any lessons learned?"""

        result = query({
            "question": question,
            "n_results": n_results,
        })

        return {
            "status": "success",
            "similar_cases": result.get("answer", ""),
            "references": result.get("sources", []),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

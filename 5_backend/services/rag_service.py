"""
RAG Service
Handles retrieval-augmented generation for policy queries.
"""

import sys
from pathlib import Path
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "4_endpoints"))


class RAGService:
    """Service for RAG operations."""

    def __init__(self):
        self.endpoint_url = None

    async def query_policies(
        self,
        question: str,
        n_results: int = 5
    ) -> dict:
        """Query policy documents."""
        try:
            from serve_rag import query

            result = query({
                "question": question,
                "n_results": n_results,
            })
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "answer": "Unable to retrieve policy information.",
            }

    async def query_with_context(
        self,
        question: str,
        application_id: Optional[str] = None,
        risk_context: Optional[dict] = None,
        n_results: int = 5
    ) -> dict:
        """Query with application context."""
        try:
            from serve_rag import query

            args = {
                "question": question,
                "n_results": n_results,
            }

            if application_id:
                args["customer_id"] = application_id
            if risk_context:
                args["risk_context"] = risk_context

            result = query(args)
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    async def get_suggested_questions(
        self,
        risk_scores: dict,
        compliance_flags: List[str]
    ) -> List[str]:
        """Generate suggested questions based on risk profile."""
        suggestions = []

        pd_score = risk_scores.get("pd_score", 0)
        if pd_score > 0.10:
            suggestions.append("What are the enhanced due diligence requirements for high-risk credits?")
            suggestions.append("What collateral requirements apply for this risk grade?")

        if pd_score > 0.05:
            suggestions.append("What is the minimum RORAC threshold for this risk grade?")
            suggestions.append("What documentation is required for senior approval?")

        if compliance_flags:
            suggestions.append("What are the compliance review requirements?")

        if not suggestions:
            suggestions = [
                "What are the standard approval criteria?",
                "What conditions typically apply to approvals?",
                "What is the monitoring frequency for this risk grade?",
            ]

        return suggestions[:4]

    async def format_response_with_sources(
        self,
        answer: str,
        sources: List[dict]
    ) -> str:
        """Format response with source citations."""
        if not sources:
            return answer

        formatted = answer + "\n\n**Sources:**\n"
        for i, source in enumerate(sources[:3], 1):
            title = source.get("title", "Unknown")
            category = source.get("category", "policy")
            formatted += f"{i}. {title} ({category})\n"

        return formatted

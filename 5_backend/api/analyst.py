"""
Analyst API Routes
AI Analyst chat and RAG query endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from services.rag_service import RAGService
from services.model_service import ModelService
from services.iceberg_service import IcebergService

router = APIRouter(prefix="/analyst", tags=["analyst"])

rag_service = RAGService()
model_service = ModelService()
db_service = IcebergService()


class ChatMessage(BaseModel):
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    application_id: Optional[str] = None
    message: str
    conversation_history: List[ChatMessage] = []
    include_risk_context: bool = True


class PolicyQueryRequest(BaseModel):
    question: str
    n_results: int = 5


class SuggestionsRequest(BaseModel):
    application_id: str


@router.post("/chat", response_model=dict)
async def chat_with_analyst(request: ChatRequest):
    """Chat with the AI analyst about an application."""
    try:
        risk_context = None
        application = None

        # Get application context if provided
        if request.application_id:
            application = db_service.get_application(request.application_id)
            if not application:
                raise HTTPException(
                    status_code=404,
                    detail=f"Application {request.application_id} not found"
                )

            if request.include_risk_context:
                # Get risk scores if available
                decision = db_service.get_decision(request.application_id)
                if decision:
                    risk_context = {
                        "pd_score": decision.get("pd_at_decision"),
                        "lgd_score": decision.get("lgd_at_decision"),
                        "expected_loss": decision.get("el_at_decision"),
                    }

        # Query RAG with context
        result = await rag_service.query_with_context(
            question=request.message,
            application_id=request.application_id,
            risk_context=risk_context,
            n_results=5
        )

        # Format response
        response = {
            "status": "success",
            "message": {
                "role": "assistant",
                "content": result.get("answer", "I don't have enough information to answer that question."),
                "timestamp": datetime.now().isoformat(),
            },
            "sources": result.get("sources", []),
        }

        if application:
            response["application_context"] = {
                "company_name": application.get("company_name"),
                "status": application.get("status"),
                "requested_amount": application.get("requested_amount"),
            }

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query-policies", response_model=dict)
async def query_policies(request: PolicyQueryRequest):
    """Query policy documents without application context."""
    try:
        result = await rag_service.query_policies(
            question=request.question,
            n_results=request.n_results
        )

        # Format with sources
        formatted_response = await rag_service.format_response_with_sources(
            answer=result.get("answer", ""),
            sources=result.get("sources", [])
        )

        return {
            "status": "success",
            "answer": result.get("answer", ""),
            "formatted_answer": formatted_response,
            "sources": result.get("sources", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestions", response_model=dict)
async def get_suggested_questions(request: SuggestionsRequest):
    """Get suggested questions based on application risk profile."""
    try:
        application = db_service.get_application(request.application_id)
        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {request.application_id} not found"
            )

        # Get decision/risk scores
        decision = db_service.get_decision(request.application_id)

        risk_scores = {}
        compliance_flags = []

        if decision:
            risk_scores = {
                "pd_score": decision.get("pd_at_decision", 0.05),
                "lgd_score": decision.get("lgd_at_decision", 0.4),
                "expected_loss": decision.get("el_at_decision", 0),
            }

        suggestions = await rag_service.get_suggested_questions(
            risk_scores=risk_scores,
            compliance_flags=compliance_flags
        )

        return {
            "status": "success",
            "suggestions": suggestions,
            "risk_profile": risk_scores,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{application_id}/risk-summary", response_model=dict)
async def get_risk_summary(application_id: str):
    """Get a comprehensive risk summary for an application."""
    try:
        application = db_service.get_application(application_id)
        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {application_id} not found"
            )

        decision = db_service.get_decision(application_id)

        # Get risk grade
        pd_score = decision.get("pd_at_decision", 0.05) if decision else 0.05
        risk_grade = await model_service.get_risk_grade(pd_score)

        summary = {
            "application_id": application_id,
            "company_name": application.get("company_name"),
            "requested_amount": application.get("requested_amount"),
            "status": application.get("status"),
            "risk_metrics": {
                "pd_score": pd_score,
                "lgd_score": decision.get("lgd_at_decision") if decision else None,
                "expected_loss": decision.get("el_at_decision") if decision else None,
                "risk_grade": risk_grade,
            },
            "decision": {
                "outcome": decision.get("final_decision") if decision else None,
                "type": decision.get("decision_type") if decision else None,
                "reason": decision.get("decision_reason") if decision else None,
            } if decision else None,
        }

        return {
            "status": "success",
            "summary": summary,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{application_id}/notes", response_model=dict)
async def add_analyst_note(
    application_id: str,
    note: str,
    note_type: str = "general"
):
    """Add an analyst note to an application."""
    try:
        application = db_service.get_application(application_id)
        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {application_id} not found"
            )

        # In production, save to database
        note_record = {
            "application_id": application_id,
            "note": note,
            "note_type": note_type,
            "created_at": datetime.now().isoformat(),
            "created_by": "analyst",
        }

        return {
            "status": "success",
            "message": "Note added successfully",
            "note": note_record,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{application_id}/compliance-check", response_model=dict)
async def check_compliance(application_id: str):
    """Get compliance check results for an application."""
    try:
        application = db_service.get_application(application_id)
        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application {application_id} not found"
            )

        # Query compliance policies
        industry = application.get("industry", "General")
        compliance_query = await rag_service.query_policies(
            question=f"What are the compliance requirements for a {industry} company loan?",
            n_results=3
        )

        return {
            "status": "success",
            "application_id": application_id,
            "compliance_guidance": compliance_query.get("answer", ""),
            "sources": compliance_query.get("sources", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
State definition for Credit Risk Reasoning Agent

Canvas-style state that tracks:
- User query and conversation history
- Reasoning steps with tool calls and results
- Computed metrics and intermediate values
- Final response assembly
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime


class ReasoningStepType(str, Enum):
    """Types of reasoning steps in the canvas"""
    QUERY_ANALYSIS = "query_analysis"
    TOOL_CALL = "tool_call"
    COMPUTATION = "computation"
    RAG_RETRIEVAL = "rag_retrieval"
    AGGREGATION = "aggregation"
    RESPONSE_GENERATION = "response_generation"


@dataclass
class ReasoningStep:
    """A single step in the reasoning canvas"""
    step_id: str
    step_type: ReasoningStepType
    title: str
    input_data: dict[str, Any]
    output_data: Optional[dict[str, Any]] = None
    status: str = "pending"  # pending, running, completed, failed
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "title": self.title,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "status": self.status,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class PortfolioContext:
    """Portfolio context for reasoning"""
    total_exposure: float = 0.0
    loan_count: int = 0
    avg_pd: float = 0.0
    avg_lgd: float = 0.0
    expected_loss: float = 0.0
    var_999: float = 0.0
    regulatory_capital: float = 0.0
    economic_capital: float = 0.0
    risk_weighted_assets: float = 0.0
    concentration_hhi: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "total_exposure": self.total_exposure,
            "loan_count": self.loan_count,
            "avg_pd": self.avg_pd,
            "avg_lgd": self.avg_lgd,
            "expected_loss": self.expected_loss,
            "var_999": self.var_999,
            "regulatory_capital": self.regulatory_capital,
            "economic_capital": self.economic_capital,
            "risk_weighted_assets": self.risk_weighted_assets,
            "concentration_hhi": self.concentration_hhi,
        }


@dataclass
class LoanContext:
    """Single loan context for detailed analysis"""
    loan_id: str
    company_name: str
    pd_score: float
    lgd_score: float
    exposure: float
    risk_grade: str
    industry: str
    region: str
    expected_loss: float = 0.0
    regulatory_capital: float = 0.0

    def to_dict(self) -> dict:
        return {
            "loan_id": self.loan_id,
            "company_name": self.company_name,
            "pd_score": self.pd_score,
            "lgd_score": self.lgd_score,
            "exposure": self.exposure,
            "risk_grade": self.risk_grade,
            "industry": self.industry,
            "region": self.region,
            "expected_loss": self.expected_loss,
            "regulatory_capital": self.regulatory_capital,
        }


@dataclass
class AgentState:
    """
    Main state for the credit risk reasoning agent

    This state flows through the LangGraph canvas, accumulating
    reasoning steps and computed results.
    """
    # Input
    query: str
    conversation_history: list[dict[str, str]] = field(default_factory=list)

    # Query understanding
    query_intent: Optional[str] = None
    entities_extracted: dict[str, Any] = field(default_factory=dict)
    requires_computation: bool = False
    requires_rag: bool = False
    target_loan_id: Optional[str] = None

    # Canvas reasoning steps
    reasoning_steps: list[ReasoningStep] = field(default_factory=list)
    current_step_index: int = 0

    # Context
    portfolio_context: Optional[PortfolioContext] = None
    loan_context: Optional[LoanContext] = None
    rag_documents: list[dict[str, Any]] = field(default_factory=list)

    # Computed metrics (on-the-fly calculations)
    computed_metrics: dict[str, Any] = field(default_factory=dict)

    # Tool results
    tool_results: dict[str, Any] = field(default_factory=dict)

    # Output
    response: Optional[str] = None
    sources: list[dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0

    # Status
    status: str = "initialized"  # initialized, analyzing, computing, generating, completed, error
    error: Optional[str] = None

    def add_reasoning_step(self, step: ReasoningStep) -> None:
        """Add a reasoning step to the canvas"""
        self.reasoning_steps.append(step)
        self.current_step_index = len(self.reasoning_steps) - 1

    def update_current_step(self, output_data: dict, status: str = "completed",
                            error: Optional[str] = None, duration_ms: Optional[int] = None) -> None:
        """Update the current reasoning step"""
        if self.reasoning_steps:
            step = self.reasoning_steps[self.current_step_index]
            step.output_data = output_data
            step.status = status
            step.error = error
            step.duration_ms = duration_ms

    def get_canvas_state(self) -> dict:
        """Get the full canvas state for visualization"""
        return {
            "query": self.query,
            "status": self.status,
            "steps": [step.to_dict() for step in self.reasoning_steps],
            "portfolio_context": self.portfolio_context.to_dict() if self.portfolio_context else None,
            "loan_context": self.loan_context.to_dict() if self.loan_context else None,
            "computed_metrics": self.computed_metrics,
            "response": self.response,
            "sources": self.sources,
            "confidence": self.confidence,
        }

    def to_dict(self) -> dict:
        """Convert full state to dictionary"""
        return {
            "query": self.query,
            "query_intent": self.query_intent,
            "entities_extracted": self.entities_extracted,
            "requires_computation": self.requires_computation,
            "requires_rag": self.requires_rag,
            "target_loan_id": self.target_loan_id,
            "reasoning_steps": [s.to_dict() for s in self.reasoning_steps],
            "portfolio_context": self.portfolio_context.to_dict() if self.portfolio_context else None,
            "loan_context": self.loan_context.to_dict() if self.loan_context else None,
            "rag_documents": self.rag_documents,
            "computed_metrics": self.computed_metrics,
            "tool_results": self.tool_results,
            "response": self.response,
            "sources": self.sources,
            "confidence": self.confidence,
            "status": self.status,
            "error": self.error,
        }


# Type alias for LangGraph
from typing import TypedDict

class GraphState(TypedDict, total=False):
    """LangGraph-compatible state dictionary"""
    query: str
    conversation_history: list[dict[str, str]]
    query_intent: str
    entities_extracted: dict[str, Any]
    requires_computation: bool
    requires_rag: bool
    target_loan_id: str
    reasoning_steps: list[dict]
    portfolio_context: dict
    loan_context: dict
    rag_documents: list[dict]
    computed_metrics: dict[str, Any]
    tool_results: dict[str, Any]
    response: str
    sources: list[dict[str, str]]
    confidence: float
    status: str
    error: str

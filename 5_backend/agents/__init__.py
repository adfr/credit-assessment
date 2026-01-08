"""
Credit Risk Reasoning Agent

Canvas-style agent for on-the-fly credit risk computations.
"""

from .graph import (
    reasoning_graph,
    run_reasoning_agent,
    run_reasoning_agent_sync,
    create_reasoning_graph,
)

from .state import (
    AgentState,
    GraphState,
    ReasoningStep,
    ReasoningStepType,
    PortfolioContext,
    LoanContext,
)

__all__ = [
    # Graph
    "reasoning_graph",
    "run_reasoning_agent",
    "run_reasoning_agent_sync",
    "create_reasoning_graph",
    # State
    "AgentState",
    "GraphState",
    "ReasoningStep",
    "ReasoningStepType",
    "PortfolioContext",
    "LoanContext",
]

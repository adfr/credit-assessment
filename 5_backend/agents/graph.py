"""
Credit Risk Reasoning Agent - LangGraph Canvas

This module implements a canvas-style reasoning agent that:
1. Analyzes user queries about credit risk
2. Executes on-the-fly computations using tools
3. Retrieves relevant policy context via RAG
4. Generates responses with full reasoning trace

The canvas shows each step of the reasoning process for transparency.
"""

import os
import time
import uuid
from typing import Any, Literal

from langgraph.graph import StateGraph, END

from .state import GraphState, ReasoningStep, ReasoningStepType


# Tool imports
from .tools.portfolio_tools import (
    get_portfolio_summary,
    get_concentration_analysis,
    get_risk_distribution,
    get_large_exposures,
)
from .tools.calculation_tools import (
    calculate_expected_loss,
    calculate_regulatory_capital,
    calculate_economic_capital,
    calculate_var,
    calculate_rorac,
    calculate_risk_grade,
)
from .tools.loan_tools import (
    get_loan_details,
    get_loan_risk_metrics,
)
from .tools.rag_tools import (
    query_policies,
    get_relevant_context,
)


def _create_step(step_type: ReasoningStepType, title: str, input_data: dict) -> dict:
    """Create a reasoning step dictionary"""
    return {
        "step_id": str(uuid.uuid4())[:8],
        "step_type": step_type.value,
        "title": title,
        "input_data": input_data,
        "output_data": None,
        "status": "running",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _update_step(step: dict, output_data: dict, status: str = "completed") -> dict:
    """Update a reasoning step with results"""
    step["output_data"] = output_data
    step["status"] = status
    return step


# ============================================================================
# Graph Nodes
# ============================================================================

def analyze_query(state: GraphState) -> GraphState:
    """
    Analyze the user query to understand intent and required actions

    Determines:
    - Query intent (portfolio_overview, loan_detail, calculation, policy_question)
    - Whether computation is needed
    - Whether RAG retrieval is needed
    - Target entities (loan IDs, metrics, etc.)
    """
    start_time = time.time()
    query = state.get("query", "").lower()

    # Create reasoning step
    step = _create_step(
        ReasoningStepType.QUERY_ANALYSIS,
        "Analyzing Query",
        {"query": state.get("query")}
    )

    # Determine intent
    intent = "general"
    requires_computation = False
    requires_rag = False
    target_loan_id = None
    entities = {}

    # Intent detection
    if any(w in query for w in ["portfolio", "overview", "summary", "total"]):
        intent = "portfolio_overview"
        requires_computation = True

    elif any(w in query for w in ["concentration", "hhi", "industry", "region"]):
        intent = "concentration_analysis"
        requires_computation = True

    elif any(w in query for w in ["var", "value at risk", "capital"]):
        intent = "risk_metrics"
        requires_computation = True

    elif any(w in query for w in ["loan", "company", "detail"]):
        intent = "loan_detail"
        # Try to extract loan ID
        import re
        loan_match = re.search(r'LOAN-\w+', state.get("query", ""), re.IGNORECASE)
        if loan_match:
            target_loan_id = loan_match.group()

    elif any(w in query for w in ["calculate", "compute", "what is", "how much"]):
        intent = "calculation"
        requires_computation = True

    elif any(w in query for w in ["policy", "rule", "threshold", "criteria", "compliance"]):
        intent = "policy_question"
        requires_rag = True

    else:
        # Default: try RAG for general questions
        requires_rag = True

    # Extract entities
    metric_keywords = {
        "pd": "probability_of_default",
        "lgd": "loss_given_default",
        "el": "expected_loss",
        "var": "value_at_risk",
        "rwa": "risk_weighted_assets",
        "rorac": "risk_adjusted_return",
    }

    for kw, entity_type in metric_keywords.items():
        if kw in query:
            entities[entity_type] = True

    # Update step
    output = {
        "intent": intent,
        "requires_computation": requires_computation,
        "requires_rag": requires_rag,
        "target_loan_id": target_loan_id,
        "entities": entities,
    }

    duration = int((time.time() - start_time) * 1000)
    step = _update_step(step, output)
    step["duration_ms"] = duration

    # Update state
    steps = state.get("reasoning_steps", [])
    steps.append(step)

    return {
        **state,
        "query_intent": intent,
        "requires_computation": requires_computation,
        "requires_rag": requires_rag,
        "target_loan_id": target_loan_id,
        "entities_extracted": entities,
        "reasoning_steps": steps,
        "status": "analyzing",
    }


def fetch_portfolio_context(state: GraphState) -> GraphState:
    """
    Fetch portfolio context for queries that need it
    """
    start_time = time.time()

    step = _create_step(
        ReasoningStepType.TOOL_CALL,
        "Fetching Portfolio Data",
        {"action": "get_portfolio_summary"}
    )

    try:
        summary = get_portfolio_summary()
        risk_dist = get_risk_distribution()

        output = {
            "summary": summary,
            "risk_distribution": risk_dist,
        }
        step = _update_step(step, output)
    except Exception as e:
        step = _update_step(step, {"error": str(e)}, "failed")
        summary = {}
        risk_dist = {}

    duration = int((time.time() - start_time) * 1000)
    step["duration_ms"] = duration

    steps = state.get("reasoning_steps", [])
    steps.append(step)

    return {
        **state,
        "portfolio_context": summary,
        "tool_results": {
            **state.get("tool_results", {}),
            "portfolio_summary": summary,
            "risk_distribution": risk_dist,
        },
        "reasoning_steps": steps,
    }


def fetch_loan_context(state: GraphState) -> GraphState:
    """
    Fetch individual loan details
    """
    start_time = time.time()
    loan_id = state.get("target_loan_id")

    step = _create_step(
        ReasoningStepType.TOOL_CALL,
        f"Fetching Loan {loan_id}",
        {"loan_id": loan_id}
    )

    try:
        if loan_id:
            loan = get_loan_details(loan_id)
            metrics = get_loan_risk_metrics(loan_id)
            output = {"loan": loan, "metrics": metrics}
        else:
            output = {"error": "No loan ID provided"}
        step = _update_step(step, output)
    except Exception as e:
        step = _update_step(step, {"error": str(e)}, "failed")
        loan = {}
        metrics = {}

    duration = int((time.time() - start_time) * 1000)
    step["duration_ms"] = duration

    steps = state.get("reasoning_steps", [])
    steps.append(step)

    return {
        **state,
        "loan_context": loan if loan_id else None,
        "tool_results": {
            **state.get("tool_results", {}),
            "loan_details": loan if loan_id else None,
            "loan_metrics": metrics if loan_id else None,
        },
        "reasoning_steps": steps,
    }


def compute_metrics(state: GraphState) -> GraphState:
    """
    Perform on-the-fly calculations based on query
    """
    start_time = time.time()
    entities = state.get("entities_extracted", {})
    portfolio = state.get("portfolio_context", {})

    step = _create_step(
        ReasoningStepType.COMPUTATION,
        "Computing Risk Metrics",
        {"entities": entities}
    )

    computed = {}

    try:
        # Get base values
        exposure = portfolio.get("total_exposure", 1000000)
        avg_pd = portfolio.get("avg_pd", 5) / 100
        avg_lgd = portfolio.get("avg_lgd", 45) / 100

        # Compute requested metrics
        if "expected_loss" in entities or "el" in str(entities).lower():
            computed["expected_loss"] = calculate_expected_loss(exposure, avg_pd, avg_lgd)

        if "value_at_risk" in entities or "var" in str(entities).lower():
            computed["var"] = calculate_var(exposure, avg_pd, avg_lgd)

        if "risk_weighted_assets" in entities or "rwa" in str(entities).lower():
            cap = calculate_regulatory_capital(exposure, avg_pd, avg_lgd)
            computed["regulatory_capital"] = cap

        # If no specific metrics requested, compute all
        if not computed:
            computed = {
                "expected_loss": calculate_expected_loss(exposure, avg_pd, avg_lgd),
                "regulatory_capital": calculate_regulatory_capital(exposure, avg_pd, avg_lgd),
                "economic_capital": calculate_economic_capital(exposure, avg_pd, avg_lgd),
                "var": calculate_var(exposure, avg_pd, avg_lgd),
            }

        step = _update_step(step, computed)
    except Exception as e:
        step = _update_step(step, {"error": str(e)}, "failed")

    duration = int((time.time() - start_time) * 1000)
    step["duration_ms"] = duration

    steps = state.get("reasoning_steps", [])
    steps.append(step)

    return {
        **state,
        "computed_metrics": computed,
        "reasoning_steps": steps,
    }


def retrieve_rag_context(state: GraphState) -> GraphState:
    """
    Retrieve relevant policy documents using RAG
    """
    start_time = time.time()
    query = state.get("query", "")

    step = _create_step(
        ReasoningStepType.RAG_RETRIEVAL,
        "Searching Policies",
        {"query": query}
    )

    try:
        result = query_policies(query, n_results=3)
        documents = result.get("documents", [])
        step = _update_step(step, {"documents": documents, "count": len(documents)})
    except Exception as e:
        step = _update_step(step, {"error": str(e)}, "failed")
        documents = []

    duration = int((time.time() - start_time) * 1000)
    step["duration_ms"] = duration

    steps = state.get("reasoning_steps", [])
    steps.append(step)

    sources = [
        {"title": doc.get("title", "Policy"), "category": doc.get("category", "policy")}
        for doc in documents
    ]

    return {
        **state,
        "rag_documents": documents,
        "sources": sources,
        "reasoning_steps": steps,
    }


def generate_response(state: GraphState) -> GraphState:
    """
    Generate final response using Claude

    In production, this would call the Anthropic API.
    For now, generates a structured response from the gathered context.
    """
    start_time = time.time()

    step = _create_step(
        ReasoningStepType.RESPONSE_GENERATION,
        "Generating Response",
        {"intent": state.get("query_intent")}
    )

    try:
        intent = state.get("query_intent", "general")
        portfolio = state.get("portfolio_context", {})
        computed = state.get("computed_metrics", {})
        loan = state.get("loan_context")
        rag_docs = state.get("rag_documents", [])

        # Build response based on intent
        response = _build_response(intent, portfolio, computed, loan, rag_docs, state.get("query", ""))

        step = _update_step(step, {"response_length": len(response)})
        confidence = 0.85 if portfolio or computed or loan else 0.6

    except Exception as e:
        response = f"I encountered an error processing your request: {str(e)}"
        step = _update_step(step, {"error": str(e)}, "failed")
        confidence = 0.3

    duration = int((time.time() - start_time) * 1000)
    step["duration_ms"] = duration

    steps = state.get("reasoning_steps", [])
    steps.append(step)

    return {
        **state,
        "response": response,
        "confidence": confidence,
        "reasoning_steps": steps,
        "status": "completed",
    }


def _build_response(
    intent: str,
    portfolio: dict,
    computed: dict,
    loan: dict | None,
    rag_docs: list,
    query: str
) -> str:
    """Build response based on context"""

    if intent == "portfolio_overview":
        if portfolio:
            return f"""Based on the current portfolio data:

**Portfolio Summary**
- Total Exposure: ${portfolio.get('total_exposure', 0):,.0f}
- Loan Count: {portfolio.get('loan_count', 0)}
- Average PD: {portfolio.get('avg_pd', 0):.2f}%
- Average LGD: {portfolio.get('avg_lgd', 0):.2f}%

**Risk Metrics**
- Expected Loss: ${portfolio.get('expected_loss', 0):,.0f}
- VaR (99.9%): ${portfolio.get('var_999', 0):,.0f}
- Regulatory Capital: ${portfolio.get('regulatory_capital', 0):,.0f}
- Risk-Weighted Assets: ${portfolio.get('risk_weighted_assets', 0):,.0f}

**Portfolio Health**
- Current: {portfolio.get('current_count', 0)} loans
- Delinquent: {portfolio.get('delinquent_count', 0)} loans
- Default: {portfolio.get('default_count', 0)} loans"""
        return "Portfolio data is not available."

    elif intent == "risk_metrics" and computed:
        parts = ["Here are the computed risk metrics:\n"]
        for metric_name, metric_data in computed.items():
            if isinstance(metric_data, dict):
                key_value = list(metric_data.values())[0]
                if isinstance(key_value, (int, float)):
                    parts.append(f"- **{metric_name.replace('_', ' ').title()}**: ${key_value:,.0f}")
        return "\n".join(parts)

    elif intent == "loan_detail" and loan:
        return f"""**Loan Details: {loan.get('loan_id', 'N/A')}**

- Company: {loan.get('company_name', 'N/A')}
- Industry: {loan.get('industry', 'N/A')}
- Outstanding Balance: ${loan.get('outstanding_balance', 0):,.0f}
- Risk Grade: {loan.get('risk_grade', 'N/A')}

**Risk Scores**
- PD Score: {(loan.get('pd_score', 0) * 100):.2f}%
- LGD Score: {(loan.get('lgd_score', 0) * 100):.2f}%
- Expected Loss: ${loan.get('expected_loss', 0):,.0f}"""

    elif intent == "policy_question" and rag_docs:
        context = "\n\n".join([doc.get("content", "")[:500] for doc in rag_docs[:2]])
        return f"Based on our credit policies:\n\n{context}"

    else:
        # General response
        if portfolio:
            return f"The portfolio currently has {portfolio.get('loan_count', 0)} loans with total exposure of ${portfolio.get('total_exposure', 0):,.0f}. How can I help you analyze it further?"
        return "I can help you analyze credit risk. Try asking about portfolio overview, specific loans, risk metrics, or our credit policies."


# ============================================================================
# Routing Logic
# ============================================================================

def route_after_analysis(state: GraphState) -> Literal["fetch_portfolio", "fetch_loan", "retrieve_rag", "generate"]:
    """Route based on query analysis"""
    intent = state.get("query_intent", "general")

    if intent in ["portfolio_overview", "concentration_analysis", "risk_metrics", "calculation"]:
        return "fetch_portfolio"
    elif intent == "loan_detail" and state.get("target_loan_id"):
        return "fetch_loan"
    elif state.get("requires_rag"):
        return "retrieve_rag"
    else:
        return "fetch_portfolio"  # Default to portfolio context


def route_after_portfolio(state: GraphState) -> Literal["compute", "retrieve_rag", "generate"]:
    """Route after fetching portfolio"""
    if state.get("requires_computation"):
        return "compute"
    elif state.get("requires_rag"):
        return "retrieve_rag"
    return "generate"


def route_after_loan(state: GraphState) -> Literal["compute", "retrieve_rag", "generate"]:
    """Route after fetching loan"""
    if state.get("requires_computation"):
        return "compute"
    elif state.get("requires_rag"):
        return "retrieve_rag"
    return "generate"


def route_after_compute(state: GraphState) -> Literal["retrieve_rag", "generate"]:
    """Route after computation"""
    if state.get("requires_rag"):
        return "retrieve_rag"
    return "generate"


# ============================================================================
# Graph Construction
# ============================================================================

def create_reasoning_graph() -> StateGraph:
    """
    Create the LangGraph canvas for credit risk reasoning

    Flow:
    1. analyze_query -> Understand intent and requirements
    2. fetch_portfolio_context OR fetch_loan_context -> Get relevant data
    3. compute_metrics -> Perform calculations if needed
    4. retrieve_rag_context -> Get policy context if needed
    5. generate_response -> Create final response
    """
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("analyze", analyze_query)
    graph.add_node("fetch_portfolio", fetch_portfolio_context)
    graph.add_node("fetch_loan", fetch_loan_context)
    graph.add_node("compute", compute_metrics)
    graph.add_node("retrieve_rag", retrieve_rag_context)
    graph.add_node("generate", generate_response)

    # Set entry point
    graph.set_entry_point("analyze")

    # Add conditional edges from analysis
    graph.add_conditional_edges(
        "analyze",
        route_after_analysis,
        {
            "fetch_portfolio": "fetch_portfolio",
            "fetch_loan": "fetch_loan",
            "retrieve_rag": "retrieve_rag",
            "generate": "generate",
        }
    )

    # Add conditional edges from portfolio fetch
    graph.add_conditional_edges(
        "fetch_portfolio",
        route_after_portfolio,
        {
            "compute": "compute",
            "retrieve_rag": "retrieve_rag",
            "generate": "generate",
        }
    )

    # Add conditional edges from loan fetch
    graph.add_conditional_edges(
        "fetch_loan",
        route_after_loan,
        {
            "compute": "compute",
            "retrieve_rag": "retrieve_rag",
            "generate": "generate",
        }
    )

    # Add conditional edges from compute
    graph.add_conditional_edges(
        "compute",
        route_after_compute,
        {
            "retrieve_rag": "retrieve_rag",
            "generate": "generate",
        }
    )

    # RAG always goes to generate
    graph.add_edge("retrieve_rag", "generate")

    # Generate is the end
    graph.add_edge("generate", END)

    return graph


# Create compiled graph
reasoning_graph = create_reasoning_graph().compile()


async def run_reasoning_agent(query: str, conversation_history: list[dict] | None = None) -> dict:
    """
    Run the reasoning agent on a query

    Args:
        query: User's question
        conversation_history: Previous conversation turns

    Returns:
        dict with response, reasoning_steps, sources, confidence
    """
    initial_state: GraphState = {
        "query": query,
        "conversation_history": conversation_history or [],
        "reasoning_steps": [],
        "status": "initialized",
    }

    result = await reasoning_graph.ainvoke(initial_state)

    return {
        "response": result.get("response", ""),
        "reasoning_steps": result.get("reasoning_steps", []),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0),
        "portfolio_context": result.get("portfolio_context"),
        "computed_metrics": result.get("computed_metrics"),
    }


def run_reasoning_agent_sync(query: str, conversation_history: list[dict] | None = None) -> dict:
    """Synchronous version of run_reasoning_agent"""
    initial_state: GraphState = {
        "query": query,
        "conversation_history": conversation_history or [],
        "reasoning_steps": [],
        "status": "initialized",
    }

    result = reasoning_graph.invoke(initial_state)

    return {
        "response": result.get("response", ""),
        "reasoning_steps": result.get("reasoning_steps", []),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0),
        "portfolio_context": result.get("portfolio_context"),
        "computed_metrics": result.get("computed_metrics"),
    }

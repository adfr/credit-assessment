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
from .tools.code_execution_tools import (
    execute_code,
    generate_scenario_code,
    get_portfolio_dataframe,
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
    requires_code_execution = False
    target_loan_id = None
    entities = {}
    scenario_params = {}

    # Intent detection - check for simulation/scenario first (highest priority)
    simulation_keywords = [
        "what if", "what happens", "simulate", "scenario", "stress",
        "impact", "sensitivity", "shock", "increase", "decrease",
        "change", "affect", "effect", "hypothetical"
    ]

    if any(w in query for w in simulation_keywords):
        intent = "simulation"
        requires_code_execution = True

        # Extract scenario parameters from query
        import re

        # Try to extract industry filter
        # Map common names to database values
        industry_map = {
            "financial": "financial_services",
            "financials": "financial_services",
            "financial services": "financial_services",
            "financial_services": "financial_services",
            "tech": "technology",
            "technology": "technology",
            "healthcare": "healthcare",
            "health care": "healthcare",
            "retail": "retail",
            "manufacturing": "manufacturing",
            "construction": "construction",
            "energy": "energy",
            "transportation": "transportation",
            "real estate": "real_estate",
            "real_estate": "real_estate",
        }

        # First, try direct industry name matching
        for name, db_value in industry_map.items():
            if name in query.lower():
                scenario_params["filter_industry"] = db_value
                break

        # If not found, try patterns
        if "filter_industry" not in scenario_params:
            industry_patterns = [
                r"(?:for|of|in)\s+(\w+(?:\s+\w+)?)\s+(?:loans|sector|industry)",
                r"(\w+(?:\s+\w+)?)\s+(?:loans|sector|industry)",
            ]
            for pattern in industry_patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    industry = match.group(1).lower().replace(" ", "_")
                    if industry in industry_map:
                        scenario_params["filter_industry"] = industry_map[industry]
                    break

        # Try to extract PD change
        pd_patterns = [
            r"pd\s+(?:increases?|goes up|rises?)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*(?:pp|percentage points?|%|percent)?",
            r"(\d+(?:\.\d+)?)\s*(?:pp|percentage points?)\s+(?:increase|rise)\s+(?:in\s+)?pd",
            r"pd\s+\+\s*(\d+(?:\.\d+)?)\s*(?:pp|%)?",
        ]
        for pattern in pd_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                pd_change = float(match.group(1))
                # Convert percentage points to decimal
                if pd_change > 1:
                    pd_change = pd_change / 100
                scenario_params["pd_change"] = pd_change
                break

        # Try to extract LGD change
        lgd_patterns = [
            r"lgd\s+(?:increases?|goes up|rises?)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*(?:pp|percentage points?|%|percent)?",
            r"(\d+(?:\.\d+)?)\s*(?:pp|percentage points?)\s+(?:increase|rise)\s+(?:in\s+)?lgd",
        ]
        for pattern in lgd_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                lgd_change = float(match.group(1))
                if lgd_change > 1:
                    lgd_change = lgd_change / 100
                scenario_params["lgd_change"] = lgd_change
                break

        # Default PD change if not specified but simulation requested
        if "pd_change" not in scenario_params and "lgd_change" not in scenario_params:
            scenario_params["pd_change"] = 0.01  # Default 1pp

    elif any(w in query for w in ["portfolio", "overview", "summary", "total"]):
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
        "requires_code_execution": requires_code_execution,
        "target_loan_id": target_loan_id,
        "entities": entities,
        "scenario_params": scenario_params,
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
        "requires_code_execution": requires_code_execution,
        "target_loan_id": target_loan_id,
        "entities_extracted": entities,
        "scenario_params": scenario_params,
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


def execute_simulation(state: GraphState) -> GraphState:
    """
    Execute Python code for scenario/simulation analysis.

    This node generates and runs Python code to perform what-if analysis,
    stress testing, and sensitivity simulations.
    """
    start_time = time.time()
    query = state.get("query", "")
    scenario_params = state.get("scenario_params", {})

    step = _create_step(
        ReasoningStepType.COMPUTATION,
        "Running Simulation",
        {
            "query": query,
            "scenario_params": scenario_params,
        }
    )

    try:
        # Build filter criteria from scenario params
        filter_criteria = {}
        if "filter_industry" in scenario_params:
            filter_criteria["industry"] = scenario_params["filter_industry"]

        # Build shock parameters
        shock_params = {}
        if "pd_change" in scenario_params:
            shock_params["pd_change"] = scenario_params["pd_change"]
        if "lgd_change" in scenario_params:
            shock_params["lgd_change"] = scenario_params["lgd_change"]

        # Default shock if none specified
        if not shock_params:
            shock_params["pd_change"] = 0.01

        # Generate scenario code
        code = generate_scenario_code(
            scenario_description=query,
            filter_criteria=filter_criteria if filter_criteria else None,
            shock_parameters=shock_params,
            metrics=["var", "expected_loss", "regulatory_capital"]
        )

        # Execute the code
        result = execute_code(code)

        if result["success"]:
            simulation_result = result.get("result", {})
            output = result.get("output", "")

            step = _update_step(step, {
                "simulation_result": simulation_result,
                "output": output,
                "code_executed": code[:500] + "..." if len(code) > 500 else code,
            })
        else:
            step = _update_step(step, {
                "error": result.get("error", "Unknown error"),
                "traceback": result.get("traceback", ""),
            }, "failed")
            simulation_result = None
            output = ""

    except Exception as e:
        step = _update_step(step, {"error": str(e)}, "failed")
        simulation_result = None
        output = ""

    duration = int((time.time() - start_time) * 1000)
    step["duration_ms"] = duration

    steps = state.get("reasoning_steps", [])
    steps.append(step)

    return {
        **state,
        "simulation_result": simulation_result,
        "simulation_output": output,
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
        simulation_result = state.get("simulation_result")
        simulation_output = state.get("simulation_output", "")

        # Build response based on intent
        response = _build_response(
            intent, portfolio, computed, loan, rag_docs,
            state.get("query", ""), simulation_result, simulation_output
        )

        step = _update_step(step, {"response_length": len(response)})
        confidence = 0.90 if simulation_result else (0.85 if portfolio or computed or loan else 0.6)

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
    query: str,
    simulation_result: dict | None = None,
    simulation_output: str = ""
) -> str:
    """Build response based on context"""

    # Handle simulation results first
    if intent == "simulation" and simulation_result:
        result = simulation_result
        baseline = result.get("baseline", {})
        stressed = result.get("stressed", {})
        impact = result.get("impact", {})

        response = f"""## Scenario Analysis Results

**Scenario:** {result.get('scenario', query)[:100]}

**Scope:**
- Affected Loans: {result.get('n_affected_loans', 'N/A')}
- Affected Exposure: ${result.get('affected_exposure', 0):,.0f}

### Baseline vs Stressed Comparison

| Metric | Baseline | Stressed | Change |
|--------|----------|----------|--------|
| VaR (99.9%) | ${baseline.get('var', 0):,.0f} | ${stressed.get('var', 0):,.0f} | {impact.get('var_change_pct', 0):+.1f}% |
| Expected Loss | ${baseline.get('expected_loss', 0):,.0f} | ${stressed.get('expected_loss', 0):,.0f} | {impact.get('el_change_pct', 0):+.1f}% |
| Regulatory Capital | ${baseline.get('regulatory_capital', 0):,.0f} | ${stressed.get('regulatory_capital', 0):,.0f} | {impact.get('capital_change_pct', 0):+.1f}% |

### Impact Summary
- **VaR Increase:** ${impact.get('var_change', 0):,.0f} ({impact.get('var_change_pct', 0):+.1f}%)
- **Additional Capital Required:** ${impact.get('capital_change', 0):,.0f}
"""
        if simulation_output:
            response += f"\n### Execution Log\n```\n{simulation_output[:1000]}\n```"

        return response

    elif intent == "simulation" and not simulation_result:
        return "I was unable to run the simulation. Please check the query format and try again."

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

def route_after_analysis(state: GraphState) -> Literal["fetch_portfolio", "fetch_loan", "retrieve_rag", "execute_simulation", "generate"]:
    """Route based on query analysis"""
    intent = state.get("query_intent", "general")

    # Simulation gets priority - goes directly to code execution
    if intent == "simulation" or state.get("requires_code_execution"):
        return "execute_simulation"
    elif intent in ["portfolio_overview", "concentration_analysis", "risk_metrics", "calculation"]:
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


def route_after_simulation(state: GraphState) -> Literal["retrieve_rag", "generate"]:
    """Route after simulation execution"""
    # Optionally fetch RAG context for policy compliance check
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
    2. fetch_portfolio_context OR fetch_loan_context OR execute_simulation -> Get data/run simulation
    3. compute_metrics -> Perform calculations if needed
    4. retrieve_rag_context -> Get policy context if needed
    5. generate_response -> Create final response

    For simulations:
    1. analyze_query -> Detect simulation intent
    2. execute_simulation -> Run Python code for scenario analysis
    3. generate_response -> Format results
    """
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("analyze", analyze_query)
    graph.add_node("fetch_portfolio", fetch_portfolio_context)
    graph.add_node("fetch_loan", fetch_loan_context)
    graph.add_node("compute", compute_metrics)
    graph.add_node("execute_simulation", execute_simulation)
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
            "execute_simulation": "execute_simulation",
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

    # Add conditional edges from simulation
    graph.add_conditional_edges(
        "execute_simulation",
        route_after_simulation,
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

# Alias for workflow API compatibility
create_workflow_graph = create_reasoning_graph


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

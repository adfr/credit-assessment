"""
Credit Risk Agent Tools

Tools for on-the-fly computations in the reasoning canvas.
"""

from .portfolio_tools import (
    get_portfolio_summary,
    get_concentration_analysis,
    get_risk_distribution,
    get_large_exposures,
)

from .calculation_tools import (
    calculate_expected_loss,
    calculate_regulatory_capital,
    calculate_economic_capital,
    calculate_var,
    calculate_rorac,
    calculate_risk_grade,
)

from .loan_tools import (
    get_loan_details,
    get_loan_risk_metrics,
    score_loan_pd,
    score_loan_lgd,
)

from .rag_tools import (
    query_policies,
    get_relevant_context,
)

__all__ = [
    # Portfolio tools
    "get_portfolio_summary",
    "get_concentration_analysis",
    "get_risk_distribution",
    "get_large_exposures",
    # Calculation tools
    "calculate_expected_loss",
    "calculate_regulatory_capital",
    "calculate_economic_capital",
    "calculate_var",
    "calculate_rorac",
    "calculate_risk_grade",
    # Loan tools
    "get_loan_details",
    "get_loan_risk_metrics",
    "score_loan_pd",
    "score_loan_lgd",
    # RAG tools
    "query_policies",
    "get_relevant_context",
]

"""
LLM-Based Credit Risk Agent

Uses Claude as the reasoning engine with tool calling for:
- Portfolio queries
- Scenario simulations
- Risk calculations
- Policy lookups (RAG)
"""

import os
import json
from typing import Any
from anthropic import Anthropic

from .tools.code_execution_tools import (
    execute_code,
    get_portfolio_dataframe,
    calculate_portfolio_var,
    calculate_regulatory_capital,
    convert_to_serializable,
)
from .tools.portfolio_tools import (
    get_portfolio_summary,
    get_concentration_analysis,
    get_risk_distribution,
)
from .tools.rag_tools import query_policies, query_company_documents
from .tools.news_tools import search_company_news, search_industry_news, search_credit_news
from .tools.loan_tools import get_loan_details, get_loan_risk_metrics, list_loans
from services.scoring_service import get_scoring_service


# Initialize Anthropic client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Define tools for Claude
TOOLS = [
    {
        "name": "get_portfolio_summary",
        "description": "Get current portfolio summary including total exposure, loan count, average PD/LGD, expected loss, regulatory capital, and risk metrics.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "run_stress_scenario",
        "description": "Run a stress test scenario by shocking PD, LGD, or asset correlation for a specific industry segment. Returns baseline vs stressed VaR, expected loss, and capital requirements using Monte Carlo simulation (100,000 iterations).",
        "input_schema": {
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "Industry to stress. Options: healthcare, energy, transportation, manufacturing, financial_services, retail, construction, technology. Use 'all' for entire portfolio.",
                    "enum": ["healthcare", "energy", "transportation", "manufacturing", "financial_services", "retail", "construction", "technology", "all"]
                },
                "pd_change": {
                    "type": "number",
                    "description": "Change in PD as decimal (e.g., 0.02 for +2 percentage points). Default 0."
                },
                "lgd_change": {
                    "type": "number",
                    "description": "Change in LGD as decimal (e.g., 0.05 for +5 percentage points). Default 0."
                },
                "correlation": {
                    "type": "number",
                    "description": "Asset correlation for Monte Carlo simulation (0 to 1). Default is 0.20. Higher correlation = higher tail risk. Typical values: 0.12-0.24 for corporates."
                }
            },
            "required": ["industry"]
        }
    },
    {
        "name": "analyze_correlation_sensitivity",
        "description": "Analyze how portfolio VaR and capital change across different asset correlation assumptions. Shows impact of correlation on tail risk using Monte Carlo simulation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "correlation_range": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "List of correlation values to test (e.g., [0.10, 0.15, 0.20, 0.25, 0.30]). Default: [0.10, 0.15, 0.20, 0.25, 0.30]"
                },
                "industry": {
                    "type": "string",
                    "description": "Industry to analyze. Use 'all' for entire portfolio.",
                    "enum": ["healthcare", "energy", "transportation", "manufacturing", "financial_services", "retail", "construction", "technology", "all"]
                }
            },
            "required": []
        }
    },
    {
        "name": "get_concentration_analysis",
        "description": "Get portfolio concentration analysis by industry, region, or risk grade. Returns HHI index and breakdown.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dimension": {
                    "type": "string",
                    "enum": ["industry", "region", "risk_grade"],
                    "description": "Dimension to analyze concentration by"
                }
            },
            "required": ["dimension"]
        }
    },
    {
        "name": "query_credit_policies",
        "description": "Search credit policy documents for information about rules, thresholds, compliance requirements, or guidelines.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question or topic to search for in policy documents"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "calculate_capital_impact",
        "description": "Calculate regulatory and economic capital for given risk parameters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "exposure": {
                    "type": "number",
                    "description": "Total exposure amount"
                },
                "pd": {
                    "type": "number",
                    "description": "Probability of default as decimal (e.g., 0.05 for 5%)"
                },
                "lgd": {
                    "type": "number",
                    "description": "Loss given default as decimal (e.g., 0.45 for 45%)"
                }
            },
            "required": ["exposure", "pd", "lgd"]
        }
    },
    {
        "name": "search_company_news",
        "description": "Search for recent news about a specific company. Useful for monitoring credit-relevant events like earnings, lawsuits, layoffs, or financial distress.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Name of the company to search for"
                },
                "query_context": {
                    "type": "string",
                    "description": "Additional context like 'bankruptcy', 'earnings', 'layoffs', 'acquisition'. Optional."
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-10). Default 5."
                },
                "time_period": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "Time period to search. Default 'week'."
                }
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "search_industry_news",
        "description": "Search for news about a specific industry sector. Useful for monitoring sector-wide credit trends and risks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "enum": ["healthcare", "energy", "technology", "financial_services", "manufacturing", "retail", "construction", "transportation"],
                    "description": "Industry sector to search"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results (1-10). Default 5."
                },
                "time_period": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "Time period to search. Default 'week'."
                }
            },
            "required": ["industry"]
        }
    },
    {
        "name": "search_credit_news",
        "description": "Search for general credit market news including default rates, credit spreads, downgrades, and market conditions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to search. Default 'corporate credit'."
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results (1-10). Default 5."
                },
                "time_period": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "Time period. Default 'week'."
                }
            },
            "required": []
        }
    },
    {
        "name": "search_company_filings",
        "description": "Search company 10-K filings and financial documents. Use this to answer questions about a company's risk factors, financial performance, business strategy, or any information from their SEC filings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'risk factors', 'revenue growth', 'debt obligations', 'competitive landscape')"
                },
                "ticker": {
                    "type": "string",
                    "description": "Optional stock ticker to filter by company (e.g., 'AAPL', 'MSFT'). If not provided, searches all companies."
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "simulate_loan_addition",
        "description": "Simulate what happens to portfolio risk if a new loan is added. Shows impact on VaR, expected loss, and capital requirements. Use this for 'what if we add X to industry Y' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "loan_amount": {
                    "type": "number",
                    "description": "Loan amount in dollars (e.g., 10000000 for $10M)"
                },
                "industry": {
                    "type": "string",
                    "enum": ["healthcare", "energy", "transportation", "manufacturing", "financial_services", "retail", "construction", "technology"],
                    "description": "Industry sector for the new loan"
                },
                "pd": {
                    "type": "number",
                    "description": "Probability of default as decimal (e.g., 0.05 for 5%). If not provided, uses industry average."
                },
                "lgd": {
                    "type": "number",
                    "description": "Loss given default as decimal (e.g., 0.45 for 45%). Default 0.45."
                },
                "correlation": {
                    "type": "number",
                    "description": "Asset correlation for VaR calculation. Default 0.20."
                }
            },
            "required": ["loan_amount", "industry"]
        }
    },
    {
        "name": "list_loans",
        "description": "List individual loans in the portfolio with optional filtering. Use this to answer questions about specific loans, find loans by criteria, or get loan-level details. Returns loan ID, company name, industry, exposure, PD, LGD, risk grade, and expected loss for each loan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "Filter by industry sector",
                    "enum": ["healthcare", "energy", "transportation", "manufacturing", "financial_services", "retail", "construction", "technology"]
                },
                "risk_grade": {
                    "type": "string",
                    "description": "Filter by risk grade (A, B, C, D, E)",
                    "enum": ["A", "B", "C", "D", "E"]
                },
                "payment_status": {
                    "type": "string",
                    "description": "Filter by payment status",
                    "enum": ["current", "delinquent", "default"]
                },
                "min_exposure": {
                    "type": "number",
                    "description": "Minimum outstanding balance filter"
                },
                "max_exposure": {
                    "type": "number",
                    "description": "Maximum outstanding balance filter"
                },
                "min_pd": {
                    "type": "number",
                    "description": "Minimum PD score filter (e.g., 0.05 for 5%)"
                },
                "max_pd": {
                    "type": "number",
                    "description": "Maximum PD score filter"
                },
                "sort_by": {
                    "type": "string",
                    "description": "Field to sort by",
                    "enum": ["outstanding_balance", "pd_score", "lgd_score", "company_name", "risk_grade"]
                },
                "sort_order": {
                    "type": "string",
                    "description": "Sort order",
                    "enum": ["asc", "desc"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of loans to return (default 20, max 100)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_loan_details",
        "description": "Get detailed information about a specific loan by its ID. Returns full loan details including company info, exposure, PD/LGD scores, risk grade, expected loss, regulatory capital, and payment history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "loan_id": {
                    "type": "string",
                    "description": "The loan ID (e.g., 'LOAN-001')"
                }
            },
            "required": ["loan_id"]
        }
    },
    {
        "name": "get_loan_risk_metrics",
        "description": "Get comprehensive risk metrics for a specific loan including expected loss, regulatory capital, economic capital, VaR, and RORAC.",
        "input_schema": {
            "type": "object",
            "properties": {
                "loan_id": {
                    "type": "string",
                    "description": "The loan ID (e.g., 'LOAN-001')"
                }
            },
            "required": ["loan_id"]
        }
    },
    {
        "name": "score_company_pd",
        "description": "Score a company for Probability of Default (PD) using the trained ML model. Takes company financials and returns PD score, risk grade, and decision recommendation. Use this when asked to rate a company, assess creditworthiness, or predict default probability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Name of the company being scored"
                },
                "annual_revenue": {
                    "type": "number",
                    "description": "Annual revenue in dollars"
                },
                "net_income": {
                    "type": "number",
                    "description": "Net income in dollars (can be negative)"
                },
                "total_assets": {
                    "type": "number",
                    "description": "Total assets in dollars"
                },
                "total_liabilities": {
                    "type": "number",
                    "description": "Total liabilities in dollars"
                },
                "industry": {
                    "type": "string",
                    "description": "Industry sector",
                    "enum": ["healthcare", "energy", "transportation", "manufacturing", "financial_services", "retail", "construction", "technology"]
                },
                "years_in_business": {
                    "type": "integer",
                    "description": "Years the company has been operating. Default 5."
                },
                "credit_score": {
                    "type": "number",
                    "description": "Credit score on 0-100 scale (0=worst, 100=best). Default 70."
                },
                "requested_loan_amount": {
                    "type": "number",
                    "description": "Loan amount being requested. Default $1,000,000."
                }
            },
            "required": ["company_name", "annual_revenue", "total_assets", "total_liabilities", "industry"]
        }
    },
    {
        "name": "score_loan_lgd",
        "description": "Score a loan for Loss Given Default (LGD) using the trained ML model. Takes collateral and loan details, returns expected loss severity if default occurs. Use this to assess recovery expectations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "loan_amount": {
                    "type": "number",
                    "description": "Loan principal amount in dollars"
                },
                "collateral_type": {
                    "type": "string",
                    "description": "Type of collateral securing the loan",
                    "enum": ["real_estate", "equipment", "inventory", "receivables", "securities", "cash", "unsecured"]
                },
                "collateral_value": {
                    "type": "number",
                    "description": "Estimated value of collateral in dollars. Required if collateral_type is not 'unsecured'."
                },
                "seniority": {
                    "type": "string",
                    "description": "Loan seniority in capital structure",
                    "enum": ["senior_secured", "senior_unsecured", "subordinated"],
                    "default": "senior_secured"
                },
                "term_months": {
                    "type": "integer",
                    "description": "Loan term in months. Default 36."
                },
                "industry": {
                    "type": "string",
                    "description": "Borrower's industry sector",
                    "enum": ["healthcare", "energy", "transportation", "manufacturing", "financial_services", "retail", "construction", "technology"]
                }
            },
            "required": ["loan_amount", "collateral_type"]
        }
    },
    {
        "name": "score_full_application",
        "description": "Complete credit application scoring combining PD and LGD models. Returns comprehensive risk assessment including expected loss, economic capital, RORAC, and decision recommendation. Use this for full underwriting analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Name of the company"
                },
                "annual_revenue": {
                    "type": "number",
                    "description": "Annual revenue in dollars"
                },
                "net_income": {
                    "type": "number",
                    "description": "Net income in dollars"
                },
                "total_assets": {
                    "type": "number",
                    "description": "Total assets in dollars"
                },
                "total_liabilities": {
                    "type": "number",
                    "description": "Total liabilities in dollars"
                },
                "industry": {
                    "type": "string",
                    "description": "Industry sector",
                    "enum": ["healthcare", "energy", "transportation", "manufacturing", "financial_services", "retail", "construction", "technology"]
                },
                "requested_amount": {
                    "type": "number",
                    "description": "Loan amount requested"
                },
                "collateral_type": {
                    "type": "string",
                    "description": "Type of collateral",
                    "enum": ["real_estate", "equipment", "inventory", "receivables", "securities", "cash", "unsecured"]
                },
                "collateral_value": {
                    "type": "number",
                    "description": "Value of collateral (if applicable)"
                },
                "proposed_interest_rate": {
                    "type": "number",
                    "description": "Proposed annual interest rate as decimal (e.g., 0.065 for 6.5%). Default 0.06."
                },
                "term_months": {
                    "type": "integer",
                    "description": "Loan term in months. Default 36."
                },
                "credit_score": {
                    "type": "number",
                    "description": "Credit score on 0-100 scale (0=worst, 100=best). Default 70."
                }
            },
            "required": ["company_name", "annual_revenue", "total_assets", "total_liabilities", "industry", "requested_amount", "collateral_type"]
        }
    },
    {
        "name": "execute_simulation_code",
        "description": """Execute custom Python code for Monte Carlo simulations, scenario analysis, or complex calculations.
Use this for custom simulations that aren't covered by other tools, such as:
- Monte Carlo loss simulations with many iterations
- Custom correlation structures or copula models
- Multi-period projections or path-dependent scenarios
- Complex what-if analyses combining multiple factors

The code has access to:
- get_portfolio_dataframe(): Load loan data as pandas DataFrame (columns: loan_id, company_name, industry, region, outstanding_balance, pd_score, lgd_score, risk_grade, etc.)
- calculate_portfolio_var(exposures, pds, lgds, correlation=0.2, simulations=100000): Calculate VaR using Monte Carlo simulation
- calculate_regulatory_capital(exposures, pds, lgds): Calculate Basel IRB capital
- numpy (as np), pandas (as pd), scipy.stats (as stats)

Store final results in a variable called 'result' (dict) and use print() for progress output.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Must store results in 'result' variable."
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what the simulation does"
                }
            },
            "required": ["code", "description"]
        }
    }
]


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool and return the result."""

    if tool_name == "get_portfolio_summary":
        return get_portfolio_summary()

    elif tool_name == "run_stress_scenario":
        industry = tool_input.get("industry", "all")
        pd_change = tool_input.get("pd_change", 0)
        lgd_change = tool_input.get("lgd_change", 0)
        correlation = tool_input.get("correlation", 0.20)

        # Build and execute simulation code
        import numpy as np
        import pandas as pd
        from scipy import stats

        df = get_portfolio_dataframe()

        # Filter by industry
        if industry != "all":
            mask = df["industry"] == industry
            filtered_df = df[mask].copy()
        else:
            filtered_df = df.copy()
            mask = pd.Series([True] * len(df), index=df.index)

        if len(filtered_df) == 0:
            return {
                "error": f"No loans found for industry: {industry}",
                "available_industries": df["industry"].unique().tolist()
            }

        # Get arrays
        exposures = df["outstanding_balance"].values
        pds_baseline = df["pd_score"].values.copy()
        lgds_baseline = df["lgd_score"].values.copy()

        # Apply shock
        pds_stressed = pds_baseline.copy()
        lgds_stressed = lgds_baseline.copy()

        filter_indices = [df.index.get_loc(i) for i in filtered_df.index]
        pds_stressed[filter_indices] = np.clip(pds_stressed[filter_indices] + pd_change, 0.0001, 0.9999)
        lgds_stressed[filter_indices] = np.clip(lgds_stressed[filter_indices] + lgd_change, 0.01, 0.99)

        # Calculate metrics with correlation parameter (Monte Carlo with 100k simulations)
        baseline_var = calculate_portfolio_var(exposures, pds_baseline, lgds_baseline, correlation=0.20)
        stressed_var = calculate_portfolio_var(exposures, pds_stressed, lgds_stressed, correlation=correlation)
        baseline_cap = calculate_regulatory_capital(exposures, pds_baseline, lgds_baseline)
        stressed_cap = calculate_regulatory_capital(exposures, pds_stressed, lgds_stressed)

        return {
            "scenario": {
                "industry": industry,
                "pd_change_pp": pd_change * 100,
                "lgd_change_pp": lgd_change * 100,
                "correlation": correlation,
                "baseline_correlation": 0.20,
            },
            "affected_loans": len(filtered_df),
            "affected_exposure": float(filtered_df["outstanding_balance"].sum()),
            "baseline": {
                "var_99_9": baseline_var["var"],
                "expected_loss": baseline_var["expected_loss"],
                "economic_capital": baseline_var["economic_capital"],
                "regulatory_capital": baseline_cap["regulatory_capital"],
            },
            "stressed": {
                "var_99_9": stressed_var["var"],
                "expected_loss": stressed_var["expected_loss"],
                "economic_capital": stressed_var["economic_capital"],
                "regulatory_capital": stressed_cap["regulatory_capital"],
            },
            "impact": {
                "var_change": stressed_var["var"] - baseline_var["var"],
                "var_change_pct": (stressed_var["var"] - baseline_var["var"]) / baseline_var["var"] * 100,
                "el_change": stressed_var["expected_loss"] - baseline_var["expected_loss"],
                "capital_change": stressed_cap["regulatory_capital"] - baseline_cap["regulatory_capital"],
            }
        }

    elif tool_name == "analyze_correlation_sensitivity":
        import numpy as np

        correlation_range = tool_input.get("correlation_range", [0.10, 0.15, 0.20, 0.25, 0.30])
        industry = tool_input.get("industry", "all")

        df = get_portfolio_dataframe()

        # Filter by industry if specified
        if industry != "all":
            mask = df["industry"] == industry
            filtered_df = df[mask].copy()
        else:
            filtered_df = df.copy()

        if len(filtered_df) == 0:
            return {
                "error": f"No loans found for industry: {industry}",
                "available_industries": df["industry"].unique().tolist()
            }

        exposures = filtered_df["outstanding_balance"].values
        pds = filtered_df["pd_score"].values
        lgds = filtered_df["lgd_score"].values

        results = []
        for corr in correlation_range:
            var_result = calculate_portfolio_var(exposures, pds, lgds, correlation=corr)
            cap_result = calculate_regulatory_capital(exposures, pds, lgds)

            results.append({
                "correlation": corr,
                "var_99_9": var_result["var"],
                "expected_loss": var_result["expected_loss"],
                "economic_capital": var_result["economic_capital"],
                "regulatory_capital": cap_result["regulatory_capital"],
            })

        # Calculate sensitivity metrics
        base_idx = correlation_range.index(0.20) if 0.20 in correlation_range else 0
        base_var = results[base_idx]["var_99_9"]

        return {
            "industry": industry,
            "total_exposure": float(filtered_df["outstanding_balance"].sum()),
            "loan_count": len(filtered_df),
            "correlation_analysis": results,
            "sensitivity_summary": {
                "base_correlation": correlation_range[base_idx],
                "base_var": base_var,
                "min_var": min(r["var_99_9"] for r in results),
                "max_var": max(r["var_99_9"] for r in results),
                "var_range_pct": (max(r["var_99_9"] for r in results) - min(r["var_99_9"] for r in results)) / base_var * 100 if base_var > 0 else 0,
            }
        }

    elif tool_name == "get_concentration_analysis":
        dimension = tool_input.get("dimension", "industry")
        return get_concentration_analysis(dimension)

    elif tool_name == "query_credit_policies":
        query = tool_input.get("query", "")
        return query_policies(query, n_results=3)

    elif tool_name == "calculate_capital_impact":
        exposure = tool_input.get("exposure", 1000000)
        pd = tool_input.get("pd", 0.05)
        lgd = tool_input.get("lgd", 0.45)

        import numpy as np
        var_result = calculate_portfolio_var(
            np.array([exposure]),
            np.array([pd]),
            np.array([lgd])
        )
        cap_result = calculate_regulatory_capital(
            np.array([exposure]),
            np.array([pd]),
            np.array([lgd])
        )

        return {
            "exposure": exposure,
            "pd": pd,
            "lgd": lgd,
            "expected_loss": var_result["expected_loss"],
            "var_99_9": var_result["var"],
            "economic_capital": var_result["economic_capital"],
            "regulatory_capital": cap_result["regulatory_capital"],
            "risk_weighted_assets": cap_result["risk_weighted_assets"],
        }

    elif tool_name == "search_company_filings":
        query = tool_input.get("query", "")
        ticker = tool_input.get("ticker")
        n_results = tool_input.get("n_results", 5)
        return query_company_documents(query, ticker, n_results)

    elif tool_name == "search_company_news":
        company_name = tool_input.get("company_name", "")
        query_context = tool_input.get("query_context")
        num_results = tool_input.get("num_results", 5)
        time_period = tool_input.get("time_period", "week")
        return search_company_news(company_name, query_context, num_results, time_period)

    elif tool_name == "search_industry_news":
        industry = tool_input.get("industry", "")
        num_results = tool_input.get("num_results", 5)
        time_period = tool_input.get("time_period", "week")
        return search_industry_news(industry, num_results, time_period)

    elif tool_name == "search_credit_news":
        topic = tool_input.get("topic", "corporate credit")
        num_results = tool_input.get("num_results", 5)
        time_period = tool_input.get("time_period", "week")
        return search_credit_news(topic, num_results, time_period)

    elif tool_name == "simulate_loan_addition":
        import numpy as np

        loan_amount = tool_input.get("loan_amount", 1000000)
        industry = tool_input.get("industry", "technology")
        correlation = tool_input.get("correlation", 0.20)
        lgd = tool_input.get("lgd", 0.45)

        # Get current portfolio
        df = get_portfolio_dataframe()

        # Industry average PD (use provided or calculate from portfolio)
        industry_loans = df[df["industry"] == industry]
        if len(industry_loans) > 0:
            industry_avg_pd = industry_loans["pd_score"].mean()
        else:
            industry_avg_pd = 0.05  # Default

        pd = tool_input.get("pd", industry_avg_pd)

        # Current portfolio metrics
        current_exposures = df["outstanding_balance"].values
        current_pds = df["pd_score"].values
        current_lgds = df["lgd_score"].values

        current_var = calculate_portfolio_var(current_exposures, current_pds, current_lgds, correlation=correlation)
        current_cap = calculate_regulatory_capital(current_exposures, current_pds, current_lgds)

        # Portfolio with new loan added
        new_exposures = np.append(current_exposures, loan_amount)
        new_pds = np.append(current_pds, pd)
        new_lgds = np.append(current_lgds, lgd)

        new_var = calculate_portfolio_var(new_exposures, new_pds, new_lgds, correlation=correlation)
        new_cap = calculate_regulatory_capital(new_exposures, new_pds, new_lgds)

        # Calculate marginal impact
        marginal_var = new_var["var"] - current_var["var"]
        marginal_el = new_var["expected_loss"] - current_var["expected_loss"]
        marginal_cap = new_cap["regulatory_capital"] - current_cap["regulatory_capital"]

        # Risk-adjusted metrics for the new loan
        standalone_el = loan_amount * pd * lgd
        standalone_var = calculate_portfolio_var(
            np.array([loan_amount]), np.array([pd]), np.array([lgd]), correlation=correlation
        )

        return {
            "scenario": {
                "loan_amount": loan_amount,
                "industry": industry,
                "pd": pd,
                "lgd": lgd,
                "correlation": correlation,
            },
            "current_portfolio": {
                "total_exposure": float(current_exposures.sum()),
                "loan_count": len(df),
                "var_99_9": current_var["var"],
                "expected_loss": current_var["expected_loss"],
                "regulatory_capital": current_cap["regulatory_capital"],
            },
            "after_addition": {
                "total_exposure": float(new_exposures.sum()),
                "loan_count": len(df) + 1,
                "var_99_9": new_var["var"],
                "expected_loss": new_var["expected_loss"],
                "regulatory_capital": new_cap["regulatory_capital"],
            },
            "marginal_impact": {
                "var_increase": marginal_var,
                "var_increase_pct": (marginal_var / current_var["var"]) * 100 if current_var["var"] > 0 else 0,
                "el_increase": marginal_el,
                "capital_increase": marginal_cap,
                "capital_increase_pct": (marginal_cap / current_cap["regulatory_capital"]) * 100 if current_cap["regulatory_capital"] > 0 else 0,
            },
            "standalone_loan": {
                "expected_loss": standalone_el,
                "var_99_9": standalone_var["var"],
            },
            "diversification_benefit": {
                "var_reduction": standalone_var["var"] - marginal_var,
                "description": "Marginal VaR is less than standalone VaR due to diversification"
            }
        }

    elif tool_name == "list_loans":
        return list_loans(
            industry=tool_input.get("industry"),
            risk_grade=tool_input.get("risk_grade"),
            payment_status=tool_input.get("payment_status"),
            min_exposure=tool_input.get("min_exposure"),
            max_exposure=tool_input.get("max_exposure"),
            min_pd=tool_input.get("min_pd"),
            max_pd=tool_input.get("max_pd"),
            sort_by=tool_input.get("sort_by", "outstanding_balance"),
            sort_order=tool_input.get("sort_order", "desc"),
            limit=tool_input.get("limit", 20)
        )

    elif tool_name == "get_loan_details":
        loan_id = tool_input.get("loan_id", "")
        return get_loan_details(loan_id)

    elif tool_name == "get_loan_risk_metrics":
        loan_id = tool_input.get("loan_id", "")
        return get_loan_risk_metrics(loan_id)

    elif tool_name == "execute_simulation_code":
        code = tool_input.get("code", "")
        description = tool_input.get("description", "Custom simulation")
        result = execute_code(code)
        result["description"] = description
        return result

    elif tool_name == "score_company_pd":
        scoring_service = get_scoring_service()

        # Prepare features for PD model
        total_assets = tool_input.get("total_assets", 1000000)
        total_liabilities = tool_input.get("total_liabilities", 500000)
        annual_revenue = tool_input.get("annual_revenue", 1000000)
        net_income = tool_input.get("net_income", 50000)
        loan_amount = tool_input.get("requested_loan_amount", 1000000)
        credit_score = tool_input.get("credit_score", 70)  # 0-100 scale

        equity = max(total_assets - total_liabilities, 1)

        features = {
            "debt_to_equity": total_liabilities / equity,
            "debt_to_assets": total_liabilities / total_assets,
            "current_ratio": 1.5,
            "quick_ratio": 1.2,
            "interest_coverage_ratio": 3.0,
            "return_on_assets": net_income / total_assets if total_assets > 0 else 0.05,
            "return_on_equity": net_income / equity if equity > 0 else 0.10,
            "profit_margin": net_income / annual_revenue if annual_revenue > 0 else 0.08,
            "credit_score_normalized": credit_score / 100,
            "payment_index_trend": 5,
            "utilization_rate": 0.50,
            "derogatory_ratio": 0,
            "avg_days_past_due": 5,
            "max_days_past_due": 30,
            "dpd_volatility": 10,
            "count_30dpd": 0,
            "count_60dpd": 0,
            "count_90dpd": 0,
            "payment_consistency_score": 0.85,
            "loan_to_revenue_ratio": loan_amount / annual_revenue if annual_revenue > 0 else 1.0,
            "loan_to_assets_ratio": loan_amount / total_assets if total_assets > 0 else 1.0,
            "industry_default_rate": 0.04,
            "industry_risk_tier": 3,
        }

        result = scoring_service.predict_pd(features)
        result["company_name"] = tool_input.get("company_name", "Unknown")
        result["industry"] = tool_input.get("industry", "unknown")
        result["input_summary"] = {
            "annual_revenue": annual_revenue,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "debt_to_equity": round(total_liabilities / equity, 2),
            "credit_score": credit_score,
        }
        return result

    elif tool_name == "score_loan_lgd":
        scoring_service = get_scoring_service()

        loan_amount = tool_input.get("loan_amount", 1000000)
        collateral_type = tool_input.get("collateral_type", "unsecured")
        collateral_value = tool_input.get("collateral_value", 0)
        term_months = tool_input.get("term_months", 36)

        # Calculate LTV ratio
        ltv_ratio = loan_amount / collateral_value if collateral_value > 0 else 1.0

        features = {
            "collateral_type": collateral_type,
            "ltv_ratio": ltv_ratio,
            "loan_amount": loan_amount,
            "debt_to_equity": 1.5,
            "current_ratio": 1.5,
            "interest_coverage_ratio": 3.0,
            "credit_score_normalized": 0.70,
            "utilization_rate": 0.50,
            "loan_to_revenue_ratio": 0.5,
            "loan_to_assets_ratio": 0.3,
            "term_months": term_months,
            "interest_rate": 0.06,
            "industry_risk_tier": 3,
        }

        result = scoring_service.predict_lgd(features)
        result["input_summary"] = {
            "loan_amount": loan_amount,
            "collateral_type": collateral_type,
            "collateral_value": collateral_value,
            "ltv_ratio": round(ltv_ratio, 2),
            "seniority": tool_input.get("seniority", "senior_secured"),
        }

        # Add recovery rate
        lgd_score = result.get("lgd_score", 0.45)
        result["recovery_rate"] = round(1 - lgd_score, 4)
        result["expected_loss_amount"] = round(loan_amount * lgd_score, 2)

        return result

    elif tool_name == "score_full_application":
        scoring_service = get_scoring_service()

        customer_data = {
            "company_name": tool_input.get("company_name", "Unknown"),
            "annual_revenue": tool_input.get("annual_revenue", 1000000),
            "net_income": tool_input.get("net_income", 50000),
            "total_assets": tool_input.get("total_assets", 1000000),
            "total_liabilities": tool_input.get("total_liabilities", 500000),
            "industry": tool_input.get("industry", "unknown"),
        }

        collateral_value = tool_input.get("collateral_value", 0)
        requested_amount = tool_input.get("requested_amount", 1000000)

        loan_request = {
            "requested_amount": requested_amount,
            "collateral_type": tool_input.get("collateral_type", "unsecured"),
            "collateral_value": collateral_value,
            "ltv_ratio": requested_amount / collateral_value if collateral_value > 0 else 1.0,
            "proposed_interest_rate": tool_input.get("proposed_interest_rate", 0.06),
            "term_months": tool_input.get("term_months", 36),
        }

        bureau_data = {
            "credit_score": tool_input.get("credit_score", 70),  # 0-100 scale
            "payment_index": 80,
            "utilization_rate": 0.50,
        }

        result = scoring_service.score_application(customer_data, loan_request, bureau_data)
        result["company_name"] = customer_data["company_name"]
        result["industry"] = customer_data["industry"]
        result["loan_amount"] = requested_amount

        return result

    else:
        return {"error": f"Unknown tool: {tool_name}"}


SYSTEM_PROMPT = """You are a Credit Risk Analyst AI assistant. You help users analyze credit portfolio risk, run stress tests, search for news, and answer questions about credit policies.

You have access to these tools:

**Portfolio-Level Tools:**
1. get_portfolio_summary - Get current portfolio metrics (total exposure, loan count, avg PD/LGD, VaR, capital)
2. run_stress_scenario - Run stress tests on specific industries with PD/LGD shocks and correlation adjustments
3. analyze_correlation_sensitivity - Analyze how VaR changes across different asset correlation assumptions (Vasicek model)
4. get_concentration_analysis - Analyze portfolio concentration by industry, region, or risk grade
5. simulate_loan_addition - Simulate impact of adding a new loan to the portfolio

**Loan-Level Tools:**
6. list_loans - List individual loans with filtering (by industry, risk grade, payment status, exposure, PD). Use this to find specific loans, get top exposures, high-risk loans, or answer questions about individual borrowers.
7. get_loan_details - Get full details for a specific loan by ID (company name, exposure, PD, LGD, risk grade, capital)
8. get_loan_risk_metrics - Get comprehensive risk metrics for a loan (EL, VaR, regulatory capital, RORAC)

**Research Tools:**
9. query_credit_policies - Search credit policy documents
10. search_company_filings - Search company 10-K filings for risk factors, financial info, business strategy
11. search_company_news - Search for recent news about a specific company
12. search_industry_news - Search for news about an industry sector
13. search_credit_news - Search for general credit market news
14. calculate_capital_impact - Calculate capital for given risk parameters

**Advanced Simulation Tool:**
15. execute_simulation_code - Execute custom Python code for Monte Carlo simulations, complex scenario analyses, or custom calculations. Use this when the user asks for:
   - Monte Carlo simulations (e.g., "run 10,000 simulations of portfolio losses")
   - Custom loss distributions or tail risk analysis
   - Multi-factor stress scenarios
   - Path-dependent or time-series projections
   - Any analysis requiring custom code beyond the built-in tools

**When to use loan-level tools:**
- "Show me our largest loans" → list_loans with sort_by=outstanding_balance
- "Which loans have PD above 10%?" → list_loans with min_pd=0.10
- "Show me technology sector loans" → list_loans with industry=technology
- "What are the details for loan LOAN-001?" → get_loan_details
- "Which companies are highest risk?" → list_loans sorted by pd_score
- "Show delinquent loans" → list_loans with payment_status=delinquent

**When to use portfolio tools:**
- "What's our total exposure?" → get_portfolio_summary
- "What if energy PD increases 2%?" → run_stress_scenario
- "Show concentration by industry" → get_concentration_analysis

Available industries: healthcare, energy, transportation, manufacturing, financial_services, retail, construction, technology.
Risk grades: A (lowest risk), B, C, D, E (highest risk)
Payment statuses: current, delinquent, default

Asset correlation in Monte Carlo simulation:
- Higher correlation means defaults are more likely to happen together (systemic risk)
- Typical corporate correlations: 0.12-0.24
- Default is 0.20; stress scenarios might use 0.25-0.30
- All VaR calculations use 100,000 Monte Carlo simulations for accuracy

Always explain your analysis and what the numbers mean for risk management."""


def run_llm_agent(query: str, conversation_history: list = None) -> dict:
    """
    Run the LLM-based agent with tool calling.

    Args:
        query: User's question
        conversation_history: Previous messages

    Returns:
        dict with response, tool_calls, and metadata
    """
    messages = conversation_history or []
    messages.append({"role": "user", "content": query})

    tool_calls = []
    reasoning_steps = []

    # Initial LLM call
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages
    )

    # Process tool calls in a loop
    while response.stop_reason == "tool_use":
        # Extract tool use blocks
        tool_use_blocks = [block for block in response.content if block.type == "tool_use"]

        # Execute each tool
        tool_results = []
        for tool_use in tool_use_blocks:
            tool_name = tool_use.name
            tool_input = tool_use.input

            reasoning_steps.append({
                "type": "tool_call",
                "tool": tool_name,
                "input": tool_input,
            })

            # Execute tool
            result = execute_tool(tool_name, tool_input)

            # Serialize result to ensure JSON compatibility
            serialized_result = convert_to_serializable(result)

            tool_calls.append({
                "tool": tool_name,
                "input": tool_input,
                "output": serialized_result
            })

            reasoning_steps.append({
                "type": "tool_result",
                "tool": tool_name,
                "output": serialized_result,
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": json.dumps(serialized_result, default=str)
            })

        # Add assistant response and tool results to messages
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        # Continue conversation
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

    # Extract final text response
    final_response = ""
    for block in response.content:
        if hasattr(block, "text"):
            final_response += block.text

    return {
        "response": final_response,
        "tool_calls": tool_calls,
        "reasoning_steps": reasoning_steps,
        "model": "claude-sonnet-4-20250514",
    }

"""
Code Execution Tools for Credit Risk Reasoning Agent

Provides a sandboxed Python execution environment for running
dynamic simulations and scenario analysis.

Example queries this enables:
- "What happens to VaR if PD of financials increases by 1pp?"
- "Simulate the impact of a 20% increase in LGD for construction loans"
- "Calculate portfolio loss under a recession scenario"
"""

import io
import os
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Optional
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))


def get_db_connection():
    """Get database connection"""
    db_path = PROJECT_ROOT / "data" / "credit_risk.db"
    return sqlite3.connect(str(db_path))


def get_portfolio_dataframe() -> pd.DataFrame:
    """
    Load the full loan portfolio as a pandas DataFrame.

    Columns include:
    - loan_id, company_name, industry, region
    - outstanding_balance, original_balance
    - pd_score, lgd_score, risk_grade
    - interest_rate, term_months
    - status, payment_status
    """
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("""
            SELECT
                loan_id, company_name, industry, region,
                outstanding_balance, original_balance,
                pd_score, lgd_score, risk_grade,
                interest_rate, term_months,
                status, payment_status,
                collateral_type, collateral_value
            FROM loans
            WHERE status = 'active'
        """, conn)
        return df
    finally:
        conn.close()


def calculate_portfolio_var(
    exposures: np.ndarray,
    pds: np.ndarray,
    lgds: np.ndarray,
    confidence: float = 0.999,
    correlation: float = 0.15
) -> dict:
    """
    Calculate portfolio VaR using the Vasicek single-factor model.

    Args:
        exposures: Array of loan exposures (EAD)
        pds: Array of probability of defaults
        lgds: Array of loss given defaults
        confidence: Confidence level (default 99.9%)
        correlation: Asset correlation (default 0.15)

    Returns:
        dict with VaR, expected loss, and breakdown
    """
    # Expected loss
    el = np.sum(exposures * pds * lgds)

    # Stressed PD at confidence level (Vasicek formula)
    norm_conf = stats.norm.ppf(confidence)

    stressed_pds = stats.norm.cdf(
        (stats.norm.ppf(pds) + np.sqrt(correlation) * norm_conf) /
        np.sqrt(1 - correlation)
    )

    # Stressed loss
    stressed_loss = np.sum(exposures * stressed_pds * lgds)

    # VaR is the stressed loss
    var = stressed_loss

    # Economic capital = Unexpected loss
    ec = stressed_loss - el

    return {
        "var": float(var),
        "expected_loss": float(el),
        "economic_capital": float(ec),
        "stressed_loss": float(stressed_loss),
        "avg_stressed_pd": float(np.mean(stressed_pds)),
        "confidence": confidence,
        "correlation": correlation,
        "n_loans": len(exposures),
        "total_exposure": float(np.sum(exposures)),
    }


def calculate_regulatory_capital(
    exposures: np.ndarray,
    pds: np.ndarray,
    lgds: np.ndarray,
    maturity: float = 2.5
) -> dict:
    """
    Calculate Basel IRB regulatory capital for a portfolio.

    Args:
        exposures: Array of loan exposures
        pds: Array of probability of defaults
        lgds: Array of loss given defaults
        maturity: Effective maturity in years

    Returns:
        dict with regulatory capital and RWA
    """
    import math

    # Constrain PDs
    pds = np.clip(pds, 0.0003, 0.9999)

    total_capital = 0
    total_rwa = 0

    for exp, pd, lgd in zip(exposures, pds, lgds):
        # Asset correlation (Basel formula)
        corr = 0.12 * (1 - np.exp(-50 * pd)) / (1 - np.exp(-50)) + \
               0.24 * (1 - (1 - np.exp(-50 * pd)) / (1 - np.exp(-50)))

        # Maturity adjustment
        b = (0.11852 - 0.05478 * np.log(pd)) ** 2
        mat_adj = (1 + (maturity - 2.5) * b) / (1 - 1.5 * b)

        # Conditional PD
        norm_pd = stats.norm.ppf(pd)
        norm_999 = stats.norm.ppf(0.999)

        cond_pd = stats.norm.cdf(
            (norm_pd + np.sqrt(corr) * norm_999) / np.sqrt(1 - corr)
        )

        # Capital requirement
        k = (lgd * cond_pd - pd * lgd) * mat_adj
        rwa = k * 12.5 * exp
        capital = rwa * 0.08

        total_capital += capital
        total_rwa += rwa

    return {
        "regulatory_capital": float(total_capital),
        "risk_weighted_assets": float(total_rwa),
        "capital_ratio": float(total_capital / np.sum(exposures) * 100) if np.sum(exposures) > 0 else 0,
        "n_loans": len(exposures),
        "total_exposure": float(np.sum(exposures)),
    }


# Pre-built environment for code execution
EXECUTION_GLOBALS = {
    # Data access
    "get_portfolio_dataframe": get_portfolio_dataframe,
    "get_portfolio": get_portfolio_dataframe,  # Alias
    "load_portfolio": get_portfolio_dataframe,  # Alias

    # Calculation helpers
    "calculate_portfolio_var": calculate_portfolio_var,
    "calculate_var": calculate_portfolio_var,  # Alias
    "calculate_regulatory_capital": calculate_regulatory_capital,
    "calculate_capital": calculate_regulatory_capital,  # Alias

    # Libraries
    "np": np,
    "numpy": np,
    "pd": pd,
    "pandas": pd,
    "stats": stats,
    "scipy_stats": stats,

    # Builtins (safe subset)
    "len": len,
    "sum": sum,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "sorted": sorted,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "print": print,
    "format": format,
    "isinstance": isinstance,
    "type": type,
}

# Forbidden patterns for security
def convert_to_serializable(obj):
    """Convert numpy/pandas types to JSON-serializable Python types."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict('records')
    elif isinstance(obj, pd.Series):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    else:
        return obj


FORBIDDEN_PATTERNS = [
    "import os",
    "import sys",
    "import subprocess",
    "import shutil",
    "__import__",
    "eval(",
    "exec(",
    "open(",
    "file(",
    "compile(",
    "globals(",
    "locals(",
    "getattr(",
    "setattr(",
    "delattr(",
    "__class__",
    "__bases__",
    "__subclasses__",
    "__mro__",
    "__code__",
    "__builtins__",
]


def validate_code(code: str) -> tuple[bool, str]:
    """
    Validate code for security issues.

    Returns:
        (is_valid, error_message)
    """
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in code:
            return False, f"Forbidden pattern detected: {pattern}"
    return True, ""


def execute_code(
    code: str,
    timeout_seconds: int = 30,
    max_output_lines: int = 100
) -> dict:
    """
    Execute Python code in a sandboxed environment.

    The code has access to:
    - get_portfolio_dataframe(): Load loan data as pandas DataFrame
    - calculate_portfolio_var(exposures, pds, lgds): Calculate VaR
    - calculate_regulatory_capital(exposures, pds, lgds): Calculate Basel capital
    - numpy (as np), pandas (as pd), scipy.stats (as stats)

    Args:
        code: Python code to execute
        timeout_seconds: Maximum execution time (not enforced in this version)
        max_output_lines: Maximum lines of output to capture

    Returns:
        dict with:
        - success: bool
        - output: stdout from code
        - result: last expression value (if any)
        - error: error message if failed
        - variables: dict of created variables (excluding functions/modules)

    Example:
        code = '''
        df = get_portfolio_dataframe()
        financials = df[df['industry'] == 'Financial Services']

        # Baseline
        baseline = calculate_var(
            financials['outstanding_balance'].values,
            financials['pd_score'].values,
            financials['lgd_score'].values
        )

        # Stressed (+1pp PD)
        stressed = calculate_var(
            financials['outstanding_balance'].values,
            financials['pd_score'].values + 0.01,
            financials['lgd_score'].values
        )

        result = {
            'baseline_var': baseline['var'],
            'stressed_var': stressed['var'],
            'var_increase': stressed['var'] - baseline['var'],
            'var_increase_pct': (stressed['var'] - baseline['var']) / baseline['var'] * 100
        }
        print(f"VaR increase: ${result['var_increase']:,.0f} ({result['var_increase_pct']:.1f}%)")
        '''
    """
    # Validate code
    is_valid, error = validate_code(code)
    if not is_valid:
        return {
            "success": False,
            "output": "",
            "result": None,
            "error": f"Security validation failed: {error}",
            "variables": {},
        }

    # Create execution environment
    exec_globals = EXECUTION_GLOBALS.copy()
    exec_locals = {}

    # Capture stdout/stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Execute the code
            exec(code, exec_globals, exec_locals)

        # Get output
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()

        # Limit output lines
        output_lines = stdout_output.split('\n')
        if len(output_lines) > max_output_lines:
            stdout_output = '\n'.join(output_lines[:max_output_lines])
            stdout_output += f"\n... (truncated, {len(output_lines) - max_output_lines} more lines)"

        # Extract result variables (exclude functions, modules, DataFrames > 1000 rows)
        result_vars = {}
        for key, value in exec_locals.items():
            if key.startswith('_'):
                continue
            if callable(value):
                continue
            if isinstance(value, pd.DataFrame):
                if len(value) <= 20:
                    result_vars[key] = value.to_dict('records')
                else:
                    result_vars[key] = {
                        "_type": "DataFrame",
                        "shape": value.shape,
                        "columns": list(value.columns),
                        "head": value.head(5).to_dict('records'),
                        "summary": value.describe().to_dict() if value.select_dtypes(include=[np.number]).shape[1] > 0 else {}
                    }
            elif isinstance(value, np.ndarray):
                if value.size <= 100:
                    result_vars[key] = value.tolist()
                else:
                    result_vars[key] = {
                        "_type": "ndarray",
                        "shape": value.shape,
                        "dtype": str(value.dtype),
                        "sample": value.flatten()[:10].tolist(),
                    }
            elif isinstance(value, (dict, list, str, int, float, bool, type(None))):
                result_vars[key] = value

        # Check for 'result' variable specifically
        final_result = exec_locals.get('result', None)

        return {
            "success": True,
            "output": stdout_output,
            "stderr": stderr_output if stderr_output else None,
            "result": convert_to_serializable(final_result),
            "variables": convert_to_serializable(result_vars),
            "error": None,
        }

    except Exception as e:
        # Get full traceback
        tb = traceback.format_exc()

        return {
            "success": False,
            "output": stdout_capture.getvalue(),
            "result": None,
            "error": f"{type(e).__name__}: {str(e)}",
            "traceback": tb,
            "variables": {},
        }


def generate_scenario_code(
    scenario_description: str,
    filter_criteria: Optional[dict] = None,
    shock_parameters: Optional[dict] = None,
    metrics: Optional[list] = None
) -> str:
    """
    Generate Python code for a scenario analysis based on description.

    This is a helper that creates boilerplate code for common scenarios.

    Args:
        scenario_description: Natural language description
        filter_criteria: e.g., {"industry": "Financial Services"}
        shock_parameters: e.g., {"pd_change": 0.01, "lgd_change": 0}
        metrics: List of metrics to calculate, e.g., ["var", "expected_loss"]

    Returns:
        Python code string ready for execution
    """
    filter_criteria = filter_criteria or {}
    shock_parameters = shock_parameters or {"pd_change": 0.01}
    metrics = metrics or ["var", "expected_loss", "regulatory_capital"]

    # Build filter expression
    filter_parts = []
    for col, value in filter_criteria.items():
        if isinstance(value, str):
            filter_parts.append(f"(df['{col}'] == '{value}')")
        else:
            filter_parts.append(f"(df['{col}'] == {value})")

    filter_expr = " & ".join(filter_parts) if filter_parts else "True"
    filter_str = str(filter_criteria) if filter_criteria else '"All loans"'

    pd_change = shock_parameters.get("pd_change", 0)
    lgd_change = shock_parameters.get("lgd_change", 0)

    # Handle no-filter case
    if filter_expr == "True":
        filter_code = """# Apply filter (all loans)
filtered_df = df.copy()
mask = pd.Series([True] * len(df), index=df.index)"""
    else:
        filter_code = f"""# Apply filter
mask = {filter_expr}
filtered_df = df[mask].copy()"""

    code = f'''# Scenario: {scenario_description}
# Filter: {filter_criteria or "All loans"}
# Shock: PD change = {pd_change:+.2%}, LGD change = {lgd_change:+.2%}

# Load portfolio data
df = get_portfolio_dataframe()
print(f"Total portfolio: {{len(df)}} loans, ${{df['outstanding_balance'].sum():,.0f}} exposure")

{filter_code}
print(f"Filtered subset: {{len(filtered_df)}} loans, ${{filtered_df['outstanding_balance'].sum():,.0f}} exposure")

# Extract arrays
exposures = df['outstanding_balance'].values
pds_baseline = df['pd_score'].values.copy()
lgds_baseline = df['lgd_score'].values.copy()

# Apply shock to filtered subset
pds_stressed = pds_baseline.copy()
lgds_stressed = lgds_baseline.copy()

# Get numeric indices for the filtered loans
filter_indices = [df.index.get_loc(i) for i in filtered_df.index]
pds_stressed[filter_indices] = np.clip(pds_stressed[filter_indices] + {pd_change}, 0.0001, 0.9999)
lgds_stressed[filter_indices] = np.clip(lgds_stressed[filter_indices] + {lgd_change}, 0.01, 0.99)

# Calculate baseline metrics
baseline_var = calculate_var(exposures, pds_baseline, lgds_baseline)
baseline_capital = calculate_capital(exposures, pds_baseline, lgds_baseline)

# Calculate stressed metrics
stressed_var = calculate_var(exposures, pds_stressed, lgds_stressed)
stressed_capital = calculate_capital(exposures, pds_stressed, lgds_stressed)

# Compare results
result = {{
    "scenario": "{scenario_description}",
    "filter": {filter_str},
    "n_affected_loans": len(filtered_df),
    "affected_exposure": float(filtered_df['outstanding_balance'].sum()),

    "baseline": {{
        "var": baseline_var['var'],
        "expected_loss": baseline_var['expected_loss'],
        "economic_capital": baseline_var['economic_capital'],
        "regulatory_capital": baseline_capital['regulatory_capital'],
    }},

    "stressed": {{
        "var": stressed_var['var'],
        "expected_loss": stressed_var['expected_loss'],
        "economic_capital": stressed_var['economic_capital'],
        "regulatory_capital": stressed_capital['regulatory_capital'],
    }},

    "impact": {{
        "var_change": stressed_var['var'] - baseline_var['var'],
        "var_change_pct": (stressed_var['var'] - baseline_var['var']) / baseline_var['var'] * 100,
        "el_change": stressed_var['expected_loss'] - baseline_var['expected_loss'],
        "el_change_pct": (stressed_var['expected_loss'] - baseline_var['expected_loss']) / baseline_var['expected_loss'] * 100,
        "capital_change": stressed_capital['regulatory_capital'] - baseline_capital['regulatory_capital'],
        "capital_change_pct": (stressed_capital['regulatory_capital'] - baseline_capital['regulatory_capital']) / baseline_capital['regulatory_capital'] * 100,
    }}
}}

# Print summary
print(f"\\n=== Scenario Analysis Results ===")
print(f"Scenario: {scenario_description}")
print(f"Affected: {{result['n_affected_loans']}} loans (${{result['affected_exposure']:,.0f}} exposure)")
print(f"\\nBaseline VaR: ${{result['baseline']['var']:,.0f}}")
print(f"Stressed VaR: ${{result['stressed']['var']:,.0f}}")
print(f"VaR Impact: ${{result['impact']['var_change']:,.0f}} ({{result['impact']['var_change_pct']:+.1f}}%)")
print(f"\\nBaseline Capital: ${{result['baseline']['regulatory_capital']:,.0f}}")
print(f"Stressed Capital: ${{result['stressed']['regulatory_capital']:,.0f}}")
print(f"Capital Impact: ${{result['impact']['capital_change']:,.0f}} ({{result['impact']['capital_change_pct']:+.1f}}%)")
'''
    return code

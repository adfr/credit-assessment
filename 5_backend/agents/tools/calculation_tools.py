"""
Calculation tools for on-the-fly risk computations
"""

import math
from typing import Optional
from scipy import stats


def calculate_expected_loss(exposure: float, pd: float, lgd: float) -> dict:
    """
    Calculate Expected Loss (EL)

    EL = EAD x PD x LGD

    Args:
        exposure: Exposure at Default (EAD)
        pd: Probability of Default (as decimal, e.g., 0.05 for 5%)
        lgd: Loss Given Default (as decimal, e.g., 0.45 for 45%)

    Returns:
        dict with EL calculation breakdown
    """
    el = exposure * pd * lgd
    return {
        "expected_loss": el,
        "exposure": exposure,
        "pd": pd,
        "lgd": lgd,
        "formula": "EL = EAD x PD x LGD",
        "calculation": f"EL = {exposure:,.0f} x {pd:.4f} x {lgd:.4f} = {el:,.0f}",
    }


def calculate_regulatory_capital(
    exposure: float,
    pd: float,
    lgd: float,
    maturity: float = 2.5,
    correlation: Optional[float] = None
) -> dict:
    """
    Calculate Basel IRB Regulatory Capital

    Uses the Basel II/III IRB formula for corporate exposures.

    Args:
        exposure: Exposure at Default
        pd: Probability of Default (decimal)
        lgd: Loss Given Default (decimal)
        maturity: Effective maturity in years
        correlation: Asset correlation (if None, uses Basel formula)

    Returns:
        dict with capital calculation breakdown
    """
    # Constrain PD
    pd = max(0.0003, min(pd, 0.9999))

    # Asset correlation (Basel formula for corporates)
    if correlation is None:
        correlation = 0.12 * (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)) + \
                      0.24 * (1 - (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)))

    # Maturity adjustment
    b = (0.11852 - 0.05478 * math.log(pd)) ** 2
    maturity_adj = (1 + (maturity - 2.5) * b) / (1 - 1.5 * b)

    # Capital requirement (K)
    norm_pd = stats.norm.ppf(pd)
    norm_999 = stats.norm.ppf(0.999)

    conditional_pd = stats.norm.cdf(
        (norm_pd + math.sqrt(correlation) * norm_999) /
        math.sqrt(1 - correlation)
    )

    k = (lgd * conditional_pd - pd * lgd) * maturity_adj

    # Risk-weighted assets
    rwa = k * 12.5 * exposure

    # Capital requirement (8% of RWA)
    capital = rwa * 0.08

    return {
        "regulatory_capital": capital,
        "risk_weighted_assets": rwa,
        "capital_requirement_k": k,
        "asset_correlation": correlation,
        "maturity_adjustment": maturity_adj,
        "conditional_pd": conditional_pd,
        "exposure": exposure,
        "pd": pd,
        "lgd": lgd,
        "maturity": maturity,
    }


def calculate_economic_capital(
    exposure: float,
    pd: float,
    lgd: float,
    confidence: float = 0.999,
    correlation: float = 0.20
) -> dict:
    """
    Calculate Economic Capital using Vasicek model

    Args:
        exposure: Exposure at Default
        pd: Probability of Default (decimal)
        lgd: Loss Given Default (decimal)
        confidence: Confidence level (e.g., 0.999 for 99.9%)
        correlation: Asset correlation

    Returns:
        dict with economic capital breakdown
    """
    # Expected loss
    el = exposure * pd * lgd

    # Unexpected loss at confidence level
    norm_pd = stats.norm.ppf(pd)
    norm_conf = stats.norm.ppf(confidence)

    stress_pd = stats.norm.cdf(
        (norm_pd + math.sqrt(correlation) * norm_conf) /
        math.sqrt(1 - correlation)
    )

    stressed_loss = exposure * stress_pd * lgd

    # Economic capital = Unexpected Loss
    ec = stressed_loss - el

    return {
        "economic_capital": ec,
        "expected_loss": el,
        "stressed_loss": stressed_loss,
        "stress_pd": stress_pd,
        "confidence_level": confidence,
        "correlation": correlation,
        "exposure": exposure,
        "pd": pd,
        "lgd": lgd,
    }


def calculate_var(
    exposure: float,
    pd: float,
    lgd: float,
    confidence: float = 0.999,
    simulations: int = 100000,
    correlation: float = 0.2,
    seed: int = 42
) -> dict:
    """
    Calculate Value at Risk (VaR) using Monte Carlo simulation

    Args:
        exposure: Exposure at Default
        pd: Probability of Default (decimal)
        lgd: Loss Given Default (decimal)
        confidence: Confidence level
        simulations: Number of Monte Carlo simulations
        correlation: Asset correlation for systematic risk factor
        seed: Random seed for reproducibility

    Returns:
        dict with VaR calculation
    """
    import numpy as np
    np.random.seed(seed)

    # Constrain PD
    pd = max(0.0003, min(pd, 0.9999))

    # Default threshold (inverse normal of PD)
    threshold = stats.norm.ppf(pd)

    # Monte Carlo simulation with single-factor model
    # Z = sqrt(rho) * M + sqrt(1-rho) * epsilon
    # where M is systematic factor, epsilon is idiosyncratic
    losses = []

    for _ in range(simulations):
        # Systematic risk factor (market-wide shock)
        systematic = np.random.standard_normal()

        # Idiosyncratic factor (borrower-specific)
        idiosyncratic = np.random.standard_normal()

        # Combined factor
        z = math.sqrt(correlation) * systematic + math.sqrt(1 - correlation) * idiosyncratic

        # Default occurs if Z < threshold
        if z < threshold:
            loss = exposure * lgd
        else:
            loss = 0.0

        losses.append(loss)

    losses = np.array(losses)

    # Calculate statistics
    expected_loss = np.mean(losses)
    var = np.percentile(losses, confidence * 100)
    var_99 = np.percentile(losses, 99)

    # Expected Shortfall (CVaR) - average loss beyond VaR
    tail_losses = losses[losses >= var]
    expected_shortfall = np.mean(tail_losses) if len(tail_losses) > 0 else var

    return {
        "var": var,
        "var_99": var_99,
        "expected_loss": expected_loss,
        "expected_shortfall": expected_shortfall,
        "confidence": confidence,
        "simulations": simulations,
        "correlation": correlation,
        "exposure": exposure,
        "pd": pd,
        "lgd": lgd,
    }


def calculate_rorac(
    spread: float,
    exposure: float,
    pd: float,
    lgd: float,
    operating_cost_ratio: float = 0.01,
    funding_cost: float = 0.02
) -> dict:
    """
    Calculate Risk-Adjusted Return on Capital (RORAC)

    RORAC = (Revenue - Expected Loss - Costs) / Economic Capital

    Args:
        spread: Loan spread over funding (decimal)
        exposure: Loan exposure
        pd: Probability of Default (decimal)
        lgd: Loss Given Default (decimal)
        operating_cost_ratio: Operating costs as ratio of exposure
        funding_cost: Funding cost rate

    Returns:
        dict with RORAC calculation
    """
    # Revenue
    gross_revenue = exposure * spread

    # Costs
    el = exposure * pd * lgd
    operating_costs = exposure * operating_cost_ratio
    funding_costs = exposure * funding_cost

    # Net income
    net_income = gross_revenue - el - operating_costs

    # Economic capital (simplified)
    ec = calculate_economic_capital(exposure, pd, lgd)["economic_capital"]

    # RORAC
    rorac = (net_income / ec * 100) if ec > 0 else 0

    return {
        "rorac": rorac,
        "gross_revenue": gross_revenue,
        "expected_loss": el,
        "operating_costs": operating_costs,
        "net_income": net_income,
        "economic_capital": ec,
        "spread": spread,
        "hurdle_rate": 12.0,  # Standard hurdle
        "decision": "APPROVE" if rorac >= 12.0 else "DECLINE",
    }


def calculate_risk_grade(pd: float) -> dict:
    """
    Map PD to risk grade

    Args:
        pd: Probability of Default (decimal)

    Returns:
        dict with risk grade and thresholds
    """
    # PD thresholds for risk grades
    thresholds = [
        ("AAA", 0.0001, 0.0005),
        ("AA", 0.0005, 0.001),
        ("A", 0.001, 0.003),
        ("BBB", 0.003, 0.01),
        ("BB", 0.01, 0.03),
        ("B", 0.03, 0.08),
        ("CCC", 0.08, 0.15),
        ("CC", 0.15, 0.25),
        ("C", 0.25, 0.50),
        ("D", 0.50, 1.0),
    ]

    grade = "D"
    grade_floor = 0.50
    grade_ceiling = 1.0

    for g, floor, ceiling in thresholds:
        if pd < ceiling:
            grade = g
            grade_floor = floor
            grade_ceiling = ceiling
            break

    return {
        "risk_grade": grade,
        "pd": pd,
        "pd_floor": grade_floor,
        "pd_ceiling": grade_ceiling,
        "grade_description": _get_grade_description(grade),
    }


def _get_grade_description(grade: str) -> str:
    """Get description for risk grade"""
    descriptions = {
        "AAA": "Prime - Exceptional creditworthiness",
        "AA": "High Grade - Very strong credit quality",
        "A": "Upper Medium - Strong credit quality",
        "BBB": "Lower Medium - Adequate credit quality",
        "BB": "Non-Investment Grade - Less vulnerable to default",
        "B": "Highly Speculative - More vulnerable to default",
        "CCC": "Substantial Risk - Currently vulnerable",
        "CC": "Extremely Speculative - Highly vulnerable",
        "C": "Near Default - Imminent default",
        "D": "In Default - Payment default occurred",
    }
    return descriptions.get(grade, "Unknown")

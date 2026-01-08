"""
Capital Service
Regulatory capital (Basel IRB) and economic capital (VaR) calculations.
"""

import math
import random
from typing import List, Dict, Optional
from dataclasses import dataclass
from scipy import stats
import numpy as np


@dataclass
class LoanData:
    """Loan data for capital calculations."""
    loan_id: str
    outstanding_balance: float
    pd_score: float
    lgd_score: float
    maturity_years: float = 2.5


class CapitalService:
    """Service for calculating regulatory and economic capital."""

    def __init__(self):
        # Basel IRB parameters
        self.confidence_level = 0.999  # 99.9% for regulatory
        self.min_pd = 0.0003  # Floor PD at 0.03%
        self.min_lgd = 0.10   # Floor LGD at 10%

    # =========================================================================
    # Basel IRB Regulatory Capital
    # =========================================================================

    def calculate_asset_correlation(self, pd: float) -> float:
        """
        Calculate asset correlation R using Basel IRB formula.
        R = 0.12 * (1 - exp(-50 * PD)) / (1 - exp(-50)) +
            0.24 * (1 - (1 - exp(-50 * PD)) / (1 - exp(-50)))
        """
        pd = max(pd, self.min_pd)

        exp_factor = (1 - math.exp(-50 * pd)) / (1 - math.exp(-50))
        r = 0.12 * exp_factor + 0.24 * (1 - exp_factor)

        return r

    def calculate_maturity_adjustment(self, pd: float, maturity: float) -> float:
        """
        Calculate maturity adjustment factor b.
        b = (0.11852 - 0.05478 * ln(PD))^2
        MA = (1 + (M - 2.5) * b) / (1 - 1.5 * b)
        """
        pd = max(pd, self.min_pd)

        b = (0.11852 - 0.05478 * math.log(pd)) ** 2
        maturity_adj = (1 + (maturity - 2.5) * b) / (1 - 1.5 * b)

        return max(1.0, maturity_adj)

    def calculate_capital_requirement(
        self,
        pd: float,
        lgd: float,
        ead: float,
        maturity: float = 2.5
    ) -> Dict:
        """
        Calculate Basel IRB capital requirement for a single exposure.

        K = LGD * N[(1-R)^-0.5 * G(PD) + (R/(1-R))^0.5 * G(0.999)] - PD * LGD
        K_adjusted = K * MA
        RWA = K_adjusted * 12.5 * EAD

        Returns dict with:
        - capital_requirement: K (capital ratio)
        - risk_weighted_assets: RWA
        - regulatory_capital: RC = RWA * 8%
        """
        pd = max(pd, self.min_pd)
        lgd = max(lgd, self.min_lgd)

        # Asset correlation
        r = self.calculate_asset_correlation(pd)

        # Capital requirement formula
        # N() is standard normal CDF, G() is inverse normal CDF
        g_pd = stats.norm.ppf(pd)
        g_conf = stats.norm.ppf(self.confidence_level)

        term1 = math.sqrt(1 / (1 - r)) * g_pd
        term2 = math.sqrt(r / (1 - r)) * g_conf

        k = lgd * stats.norm.cdf(term1 + term2) - pd * lgd

        # Maturity adjustment
        ma = self.calculate_maturity_adjustment(pd, maturity)
        k_adjusted = k * ma

        # Risk-weighted assets
        rwa = k_adjusted * 12.5 * ead

        # Regulatory capital (8% of RWA)
        regulatory_capital = rwa * 0.08

        return {
            "capital_requirement": round(k_adjusted, 6),
            "risk_weighted_assets": round(rwa, 2),
            "regulatory_capital": round(regulatory_capital, 2),
            "expected_loss": round(pd * lgd * ead, 2),
        }

    def calculate_portfolio_regulatory_capital(
        self,
        loans: List[Dict]
    ) -> Dict:
        """
        Calculate total regulatory capital for a portfolio.
        """
        total_rwa = 0
        total_regulatory_capital = 0
        total_expected_loss = 0
        total_ead = 0

        loan_details = []

        for loan in loans:
            ead = loan.get("outstanding_balance", 0)
            pd = loan.get("pd_score", 0.05)
            lgd = loan.get("lgd_score", 0.45)

            # Calculate maturity in years
            term_months = loan.get("term_months", 36)
            maturity = term_months / 12

            result = self.calculate_capital_requirement(pd, lgd, ead, maturity)

            total_rwa += result["risk_weighted_assets"]
            total_regulatory_capital += result["regulatory_capital"]
            total_expected_loss += result["expected_loss"]
            total_ead += ead

            loan_details.append({
                "loan_id": loan.get("loan_id"),
                **result
            })

        return {
            "total_exposure": round(total_ead, 2),
            "total_risk_weighted_assets": round(total_rwa, 2),
            "total_regulatory_capital": round(total_regulatory_capital, 2),
            "total_expected_loss": round(total_expected_loss, 2),
            "capital_ratio": round(total_regulatory_capital / total_ead * 100, 2) if total_ead > 0 else 0,
            "risk_weight_avg": round(total_rwa / total_ead * 100, 2) if total_ead > 0 else 0,
            "loan_count": len(loans),
        }

    # =========================================================================
    # Economic Capital (VaR)
    # =========================================================================

    def calculate_var_montecarlo(
        self,
        loans: List[Dict],
        confidence: float = 0.999,
        simulations: int = 10000,
        seed: int = 42
    ) -> Dict:
        """
        Calculate Value at Risk using Monte Carlo simulation.

        For each simulation:
        1. Generate correlated default indicators
        2. Calculate portfolio loss
        3. Build loss distribution

        Returns VaR at specified confidence level.
        """
        np.random.seed(seed)

        if not loans:
            return {
                "var_99": 0,
                "var_999": 0,
                "expected_shortfall": 0,
                "economic_capital": 0,
                "expected_loss": 0,
            }

        n_loans = len(loans)

        # Extract loan parameters
        exposures = np.array([loan.get("outstanding_balance", 0) for loan in loans])
        pds = np.array([max(loan.get("pd_score", 0.05), self.min_pd) for loan in loans])
        lgds = np.array([max(loan.get("lgd_score", 0.45), self.min_lgd) for loan in loans])

        # Correlation matrix (simplified: uniform correlation of 0.2)
        correlation = 0.2
        corr_matrix = np.full((n_loans, n_loans), correlation)
        np.fill_diagonal(corr_matrix, 1.0)

        # Cholesky decomposition for correlated random numbers
        try:
            chol = np.linalg.cholesky(corr_matrix)
        except np.linalg.LinAlgError:
            # If not positive definite, use identity
            chol = np.eye(n_loans)

        # Default thresholds (inverse normal of PD)
        thresholds = stats.norm.ppf(pds)

        # Monte Carlo simulation
        losses = []

        for _ in range(simulations):
            # Generate correlated standard normal random variables
            z = np.random.standard_normal(n_loans)
            correlated_z = chol @ z

            # Determine defaults (if Z < threshold, loan defaults)
            defaults = (correlated_z < thresholds).astype(float)

            # Calculate loss for this scenario
            scenario_loss = np.sum(defaults * exposures * lgds)
            losses.append(scenario_loss)

        losses = np.array(losses)

        # Calculate statistics
        expected_loss = np.mean(losses)
        var_99 = np.percentile(losses, 99)
        var_999 = np.percentile(losses, 99.9)

        # Expected Shortfall (CVaR) - average loss beyond VaR
        tail_losses = losses[losses >= var_999]
        expected_shortfall = np.mean(tail_losses) if len(tail_losses) > 0 else var_999

        # Economic capital = Unexpected loss = VaR - EL
        economic_capital = var_999 - expected_loss

        return {
            "var_99": round(var_99, 2),
            "var_999": round(var_999, 2),
            "expected_shortfall": round(expected_shortfall, 2),
            "economic_capital": round(economic_capital, 2),
            "expected_loss": round(expected_loss, 2),
            "loss_std": round(np.std(losses), 2),
            "simulations": simulations,
        }

    # =========================================================================
    # Combined Capital Summary
    # =========================================================================

    def get_portfolio_capital_summary(self, loans: List[Dict]) -> Dict:
        """
        Get complete capital summary for portfolio.
        Combines regulatory capital and economic capital calculations.
        """
        # Regulatory capital (Basel IRB)
        reg_capital = self.calculate_portfolio_regulatory_capital(loans)

        # Economic capital (VaR)
        econ_capital = self.calculate_var_montecarlo(loans)

        # Total exposure
        total_exposure = sum(loan.get("outstanding_balance", 0) for loan in loans)

        # Capital adequacy ratios
        reg_ratio = (reg_capital["total_regulatory_capital"] / total_exposure * 100) if total_exposure > 0 else 0
        econ_ratio = (econ_capital["economic_capital"] / total_exposure * 100) if total_exposure > 0 else 0

        return {
            "total_exposure": round(total_exposure, 2),
            "loan_count": len(loans),

            # Regulatory Capital
            "regulatory_capital": reg_capital["total_regulatory_capital"],
            "risk_weighted_assets": reg_capital["total_risk_weighted_assets"],
            "reg_capital_ratio": round(reg_ratio, 2),
            "avg_risk_weight": reg_capital["risk_weight_avg"],

            # Economic Capital
            "economic_capital": econ_capital["economic_capital"],
            "var_99": econ_capital["var_99"],
            "var_999": econ_capital["var_999"],
            "expected_shortfall": econ_capital["expected_shortfall"],
            "econ_capital_ratio": round(econ_ratio, 2),

            # Expected Loss
            "expected_loss": reg_capital["total_expected_loss"],
            "el_ratio": round(reg_capital["total_expected_loss"] / total_exposure * 100, 2) if total_exposure > 0 else 0,

            # Capital Buffer
            "capital_buffer": round(
                min(reg_capital["total_regulatory_capital"], econ_capital["economic_capital"]) -
                reg_capital["total_expected_loss"],
                2
            ),
        }


# Singleton instance
_capital_service = None


def get_capital_service() -> CapitalService:
    """Get singleton instance of CapitalService."""
    global _capital_service
    if _capital_service is None:
        _capital_service = CapitalService()
    return _capital_service

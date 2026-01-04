"""
Risk Pydantic Models
Data models for risk scores and metrics.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RiskDecision(str, Enum):
    """Risk decision outcome."""
    APPROVE = "APPROVE"
    REFER = "REFER"
    DECLINE = "DECLINE"
    PENDING = "PENDING"


class RiskGrade(str, Enum):
    """Risk grade classification."""
    AAA = "AAA"
    AA = "AA"
    A = "A"
    BBB = "BBB"
    BB = "BB"
    B = "B"
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"


class RiskScores(BaseModel):
    """Complete risk scoring output."""
    # Probability metrics
    pd_score: float = Field(..., ge=0, le=1, description="Probability of Default")
    lgd_score: float = Field(..., ge=0, le=1, description="Loss Given Default")

    # Loss metrics
    expected_loss: float = Field(..., ge=0, description="Expected Loss in $")
    expected_loss_rate: float = Field(..., ge=0, le=1, description="EL as % of exposure")

    # Capital metrics
    economic_capital: float = Field(..., ge=0, description="Economic Capital requirement")
    regulatory_capital: float = Field(..., ge=0, description="Regulatory Capital requirement")
    capital_ratio: float = Field(..., ge=0, description="Capital as % of exposure")

    # Return metrics
    rorac: float = Field(..., description="Return on Risk-Adjusted Capital")
    minimum_rate: float = Field(..., ge=0, description="Minimum acceptable interest rate")

    # Classification
    risk_grade: RiskGrade
    risk_decision: RiskDecision

    # Confidence
    model_confidence: float = Field(..., ge=0, le=1, description="Model confidence score")


class RiskFactors(BaseModel):
    """Key risk factors identified."""
    financial_health: str = Field(..., description="LOW, MEDIUM, or HIGH risk")
    industry_risk: str
    credit_history: str
    collateral_coverage: str
    key_concerns: list[str] = []
    mitigating_factors: list[str] = []


class RiskAssessment(BaseModel):
    """Complete risk assessment for an application."""
    application_id: str
    scores: RiskScores
    factors: RiskFactors
    recommendation: RiskDecision
    auto_decidable: bool
    requires_review: bool
    review_reasons: list[str] = []
    conditions: list[str] = []


class ComplianceResult(BaseModel):
    """Compliance check results."""
    passed: bool
    checks_performed: list[str]
    flags: list[str] = []
    sanctions_clear: bool = True
    aml_clear: bool = True
    policy_violations: list[str] = []

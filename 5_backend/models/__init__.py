"""
Pydantic Models for Credit Risk Platform
"""

from .application import (
    ApplicationStatus,
    LoanPurpose,
    CollateralType,
    CustomerData,
    LoanRequest,
    DocumentInfo,
    ApplicationCreate,
    ApplicationResponse,
    ApplicationSummary,
    ApplicationListResponse,
)

from .workflow import (
    WorkflowStatus,
    StepStatus,
    WorkflowStep,
    StepResult,
    WorkflowState,
    WorkflowStartRequest,
    WorkflowStartResponse,
    WorkflowResumeRequest,
    WorkflowStatusResponse,
    WorkflowHistoryResponse,
)

from .risk import (
    RiskDecision,
    RiskGrade,
    RiskScores,
    RiskFactors,
    RiskAssessment,
    ComplianceResult,
)

from .decision import (
    DecisionType,
    DecisionCondition,
    DecisionResponse,
    DecisionOverrideRequest,
    AnalystNote,
    DecisionSummary,
)

__all__ = [
    # Application
    "ApplicationStatus",
    "LoanPurpose",
    "CollateralType",
    "CustomerData",
    "LoanRequest",
    "DocumentInfo",
    "ApplicationCreate",
    "ApplicationResponse",
    "ApplicationSummary",
    "ApplicationListResponse",
    # Workflow
    "WorkflowStatus",
    "StepStatus",
    "WorkflowStep",
    "StepResult",
    "WorkflowState",
    "WorkflowStartRequest",
    "WorkflowStartResponse",
    "WorkflowResumeRequest",
    "WorkflowStatusResponse",
    "WorkflowHistoryResponse",
    # Risk
    "RiskDecision",
    "RiskGrade",
    "RiskScores",
    "RiskFactors",
    "RiskAssessment",
    "ComplianceResult",
    # Decision
    "DecisionType",
    "DecisionCondition",
    "DecisionResponse",
    "DecisionOverrideRequest",
    "AnalystNote",
    "DecisionSummary",
]

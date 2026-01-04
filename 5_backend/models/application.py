"""
Application Pydantic Models
Data models for credit applications.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    """Application status enum."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class LoanPurpose(str, Enum):
    """Loan purpose enum."""
    WORKING_CAPITAL = "working_capital"
    EXPANSION = "expansion"
    EQUIPMENT = "equipment"
    ACQUISITION = "acquisition"
    REFINANCING = "refinancing"
    REAL_ESTATE = "real_estate"


class CollateralType(str, Enum):
    """Collateral type enum."""
    REAL_ESTATE = "real_estate"
    EQUIPMENT = "equipment"
    INVENTORY = "inventory"
    RECEIVABLES = "receivables"
    SECURITIES = "securities"
    UNSECURED = "unsecured"


class CustomerData(BaseModel):
    """Customer/company information."""
    company_name: str = Field(..., min_length=1, max_length=255)
    industry: str
    years_in_business: int = Field(..., ge=0)
    employee_count: Optional[int] = None
    annual_revenue: float = Field(..., gt=0)
    net_income: float
    total_assets: float = Field(..., gt=0)
    total_liabilities: float = Field(..., ge=0)

    # Financial ratios (can be calculated or provided)
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    interest_coverage_ratio: Optional[float] = None


class LoanRequest(BaseModel):
    """Loan request details."""
    requested_amount: float = Field(..., gt=100000, le=50000000)
    requested_term_months: int = Field(..., ge=12, le=120)
    purpose: LoanPurpose
    proposed_interest_rate: Optional[float] = None
    collateral_type: CollateralType = CollateralType.UNSECURED
    collateral_value: Optional[float] = None


class DocumentInfo(BaseModel):
    """Uploaded document information."""
    document_id: str
    filename: str
    document_type: str
    upload_date: datetime
    file_size: int
    status: str = "pending"
    extracted_data: Optional[dict] = None


class ApplicationCreate(BaseModel):
    """Request model for creating a new application."""
    customer: CustomerData
    loan: LoanRequest
    documents: Optional[list[DocumentInfo]] = []

    class Config:
        json_schema_extra = {
            "example": {
                "customer": {
                    "company_name": "ACME Corporation",
                    "industry": "manufacturing",
                    "years_in_business": 15,
                    "employee_count": 500,
                    "annual_revenue": 50000000,
                    "net_income": 5000000,
                    "total_assets": 40000000,
                    "total_liabilities": 20000000,
                },
                "loan": {
                    "requested_amount": 5000000,
                    "requested_term_months": 48,
                    "purpose": "equipment",
                    "collateral_type": "equipment",
                    "collateral_value": 7000000,
                }
            }
        }


class ApplicationResponse(BaseModel):
    """Response model for application details."""
    application_id: str
    status: ApplicationStatus
    customer: CustomerData
    loan: LoanRequest
    documents: list[DocumentInfo] = []
    workflow_id: Optional[str] = None
    current_step: Optional[str] = None
    submitted_at: datetime
    updated_at: datetime
    decided_at: Optional[datetime] = None


class ApplicationSummary(BaseModel):
    """Summary model for application list."""
    application_id: str
    company_name: str
    requested_amount: float
    status: ApplicationStatus
    submitted_at: datetime
    risk_grade: Optional[str] = None


class ApplicationListResponse(BaseModel):
    """Response model for application list."""
    applications: list[ApplicationSummary]
    total: int
    page: int
    page_size: int

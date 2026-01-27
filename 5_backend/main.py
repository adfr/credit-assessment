"""
Credit Risk Platform - Portfolio Risk Management API
Main entry point for the backend API.
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add paths
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
sys.path.insert(0, str(PROJECT_ROOT / "5_backend"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from config import settings
from services.portfolio_service import get_portfolio_service
from services.capital_service import get_capital_service
from services.scoring_service import get_scoring_service
from services.model_registry_service import get_model_registry, ModelType
from agents.llm_agent import run_llm_agent
from api.models import router as models_router
from api.documents import router as documents_router


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("[INFO] Starting Credit Risk Portfolio API...")
    print(f"[INFO] API running on {settings.api_host}:{settings.api_port}")
    yield
    print("[INFO] Shutting down Credit Risk Portfolio API...")


# Create FastAPI app
app = FastAPI(
    title="Credit Risk Portfolio API",
    description="API for portfolio risk management and analytics",
    version="2.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(models_router)
app.include_router(documents_router)


# Track API metrics
api_metrics = {
    "requests": 0,
    "errors": 0,
    "start_time": datetime.now(),
    "latencies": [],
}


@app.middleware("http")
async def track_metrics(request, call_next):
    """Track API metrics."""
    import time

    # Skip metrics for CORS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)

    start = time.time()
    api_metrics["requests"] += 1

    try:
        response = await call_next(request)
        latency = (time.time() - start) * 1000
        api_metrics["latencies"].append(latency)
        if len(api_metrics["latencies"]) > 1000:
            api_metrics["latencies"] = api_metrics["latencies"][-1000:]
        return response
    except Exception as e:
        api_metrics["errors"] += 1
        raise e


# CORS middleware - DISABLED because CML proxy adds CORS headers automatically
# Having both causes duplicate headers which browsers reject
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=False,
#     allow_methods=["*"],
#     allow_headers=["*"],
#     expose_headers=["*"],
# )


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
    }


# ============================================================================
# Portfolio Endpoints
# ============================================================================

@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get portfolio health summary for dashboard."""
    service = get_portfolio_service()
    return service.get_portfolio_summary()


@app.get("/api/portfolio/risk-distribution")
async def get_risk_distribution():
    """Get risk grade distribution."""
    service = get_portfolio_service()
    return service.get_risk_distribution()


@app.get("/api/portfolio/capital")
async def get_capital_metrics():
    """Get regulatory and economic capital metrics."""
    service = get_portfolio_service()
    summary = service.get_portfolio_summary()

    return {
        "regulatory_capital": summary["regulatory_capital"],
        "economic_capital": summary["economic_capital"],
        "risk_weighted_assets": summary["risk_weighted_assets"],
        "expected_loss": summary["expected_loss"],
        "var_999": summary["var_999"],
        "reg_capital_ratio": summary["reg_capital_ratio"],
        "econ_capital_ratio": summary["econ_capital_ratio"],
        "total_exposure": summary["total_exposure"],
    }


# ============================================================================
# Analytics Endpoints
# ============================================================================

@app.get("/api/analytics/concentration/{dimension}")
async def get_concentration(dimension: str):
    """
    Get concentration analysis by dimension.
    Dimensions: industry, region, risk_grade, collateral, purpose
    """
    service = get_portfolio_service()
    return service.get_concentration_analysis(dimension)


@app.get("/api/analytics/large-exposures")
async def get_large_exposures(threshold: float = Query(default=5.0, ge=1.0, le=20.0)):
    """Get large exposure report. Threshold is percentage of portfolio."""
    service = get_portfolio_service()
    return service.get_large_exposures(threshold)


@app.get("/api/analytics/migration-matrix")
async def get_migration_matrix(period: int = Query(default=12, ge=6, le=36)):
    """Get risk migration matrix."""
    service = get_portfolio_service()
    return service.get_risk_migration_matrix(period)


@app.get("/api/analytics/vintage")
async def get_vintage_analysis():
    """Get vintage analysis (default rates by origination cohort)."""
    service = get_portfolio_service()
    return service.get_vintage_analysis()


# ============================================================================
# Loan Endpoints
# ============================================================================

@app.get("/api/loans")
async def list_loans(
    status: Optional[str] = None,
    risk_grade: Optional[str] = None,
    industry: Optional[str] = None,
    region: Optional[str] = None,
    payment_status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List loans with optional filtering."""
    service = get_portfolio_service()
    return service.list_loans(
        status=status,
        risk_grade=risk_grade,
        industry=industry,
        region=region,
        payment_status=payment_status,
        limit=limit,
        offset=offset,
    )


@app.get("/api/loans/{loan_id}")
async def get_loan(loan_id: str):
    """Get individual loan details."""
    service = get_portfolio_service()
    loan = service.get_loan(loan_id)

    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    # Calculate individual capital for this loan
    capital_service = get_capital_service()
    capital = capital_service.calculate_capital_requirement(
        pd=loan["pd_score"],
        lgd=loan["lgd_score"],
        ead=loan["outstanding_balance"],
        maturity=loan["term_months"] / 12
    )

    return {
        **loan,
        "regulatory_capital": capital["regulatory_capital"],
        "expected_loss": capital["expected_loss"],
        "risk_weighted_assets": capital["risk_weighted_assets"],
    }


@app.get("/api/loans/{loan_id}/repayments")
async def get_loan_repayments(loan_id: str):
    """Get repayment history for a loan."""
    service = get_portfolio_service()

    # Verify loan exists
    loan = service.get_loan(loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    repayments = service.get_loan_repayments(loan_id)
    return {
        "loan_id": loan_id,
        "repayments": repayments,
        "count": len(repayments),
    }


class LoanCreate(BaseModel):
    """Request model for adding a new loan."""
    company_name: str
    industry: str
    region: str
    country: str
    loan_amount: float
    interest_rate: float = 0.05
    term_months: int = 36
    purpose: str = "working_capital"
    collateral_type: str = "unsecured"
    collateral_value: float = 0
    # Risk scores - optional, will be predicted by models if not provided
    pd_score: Optional[float] = None
    lgd_score: Optional[float] = None
    risk_grade: Optional[str] = None
    # Company financials for model prediction
    annual_revenue: float = 0
    net_income: float = 0
    total_assets: float = 0
    total_liabilities: float = 0


@app.post("/api/loans")
async def add_loan(loan: LoanCreate):
    """Add a new loan to the portfolio with model-predicted PD/LGD."""
    loan_data = loan.model_dump()

    # If PD/LGD not provided, predict using scoring models
    if loan_data.get("pd_score") is None or loan_data.get("lgd_score") is None:
        scoring_service = get_scoring_service()

        # Prepare customer and loan data for scoring
        customer_data = {
            "annual_revenue": loan_data.get("annual_revenue", 1000000),
            "net_income": loan_data.get("net_income", 100000),
            "total_assets": loan_data.get("total_assets", 5000000),
            "total_liabilities": loan_data.get("total_liabilities", 2000000),
        }
        loan_request = {
            "requested_amount": loan_data["loan_amount"],
            "proposed_interest_rate": loan_data.get("interest_rate", 0.05),
            "term_months": loan_data.get("term_months", 36),
            "collateral_type": loan_data.get("collateral_type", "unsecured"),
            "ltv_ratio": (
                loan_data["loan_amount"] / loan_data.get("collateral_value", loan_data["loan_amount"])
                if loan_data.get("collateral_value", 0) > 0
                else 1.0
            ),
        }

        # Get model predictions
        scoring_result = scoring_service.score_application(customer_data, loan_request)

        # Use model predictions
        loan_data["pd_score"] = scoring_result["pd_score"]
        loan_data["lgd_score"] = scoring_result["lgd_score"]
        loan_data["risk_grade"] = scoring_result["risk_grade"]

    service = get_portfolio_service()
    result = service.add_loan(loan_data)

    # Include scoring info in response
    result["scoring_source"] = "model" if loan.pd_score is None else "manual"
    return result


# ============================================================================
# AI Assistant Endpoints
# ============================================================================

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    include_portfolio_context: bool = True


@app.post("/api/assistant/chat")
async def assistant_chat(request: ChatRequest):
    """AI assistant for portfolio questions with simulation capability."""
    try:
        # Use the LLM agent with tool calling
        result = run_llm_agent(
            query=request.message,
            conversation_history=[]
        )

        # Get portfolio summary for context if requested
        portfolio_summary = None
        if request.include_portfolio_context:
            service = get_portfolio_service()
            portfolio_summary = service.get_portfolio_summary()

        return {
            "message": result.get("response", "Unable to generate response"),
            "sources": [],
            "reasoning_steps": result.get("reasoning_steps", []),
            "tool_calls": result.get("tool_calls", []),
            "model": result.get("model"),
            "portfolio_context": portfolio_summary,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "message": f"Error processing request: {str(e)}",
            "sources": [],
            "portfolio_context": None,
        }


# ============================================================================
# Monitoring Endpoints
# ============================================================================

@app.get("/api/monitoring/metrics")
async def get_monitoring_metrics():
    """Get model and system metrics."""
    registry = get_model_registry()

    # Get active PD model
    pd_metrics = {"status": "no_active_model", "model_id": None}
    pd_model = registry.get_active_model(ModelType.PD)
    if pd_model:
        pd_metrics = {
            "status": "healthy",
            "model_id": pd_model.model_id,
            "model_name": pd_model.model_name,
            "version": pd_model.version,
            "framework": pd_model.framework,
            "trained_at": pd_model.training_date,
            **(pd_model.metrics or {})
        }

    # Get active LGD model
    lgd_metrics = {"status": "no_active_model", "model_id": None}
    lgd_model = registry.get_active_model(ModelType.LGD)
    if lgd_model:
        lgd_metrics = {
            "status": "healthy",
            "model_id": lgd_model.model_id,
            "model_name": lgd_model.model_name,
            "version": lgd_model.version,
            "framework": lgd_model.framework,
            "trained_at": lgd_model.training_date,
            **(lgd_model.metrics or {})
        }

    # Get all registered models count
    all_models = registry.list_models()
    pd_models = [m for m in all_models if m.model_type == "pd"]
    lgd_models = [m for m in all_models if m.model_type == "lgd"]

    # System metrics
    uptime_seconds = (datetime.now() - api_metrics["start_time"]).total_seconds()
    avg_latency = sum(api_metrics["latencies"]) / len(api_metrics["latencies"]) if api_metrics["latencies"] else 0
    error_rate = (api_metrics["errors"] / api_metrics["requests"] * 100) if api_metrics["requests"] > 0 else 0

    # Get portfolio stats
    service = get_portfolio_service()
    summary = service.get_portfolio_summary()

    return {
        "pd_model": pd_metrics,
        "lgd_model": lgd_metrics,
        "models_summary": {
            "total_pd_models": len(pd_models),
            "total_lgd_models": len(lgd_models),
            "active_pd": pd_model.model_name if pd_model else None,
            "active_lgd": lgd_model.model_name if lgd_model else None,
        },
        "system": {
            "uptime_seconds": uptime_seconds,
            "total_requests": api_metrics["requests"],
            "total_errors": api_metrics["errors"],
            "error_rate_percent": round(error_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "loans_count": summary["loan_count"],
            "total_exposure": summary["total_exposure"],
        }
    }


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )

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
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from services.portfolio_service import get_portfolio_service
from services.capital_service import get_capital_service


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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    pd_score: float = 0.05
    lgd_score: float = 0.45
    risk_grade: str = "BBB"
    annual_revenue: float = 0
    net_income: float = 0
    total_assets: float = 0
    total_liabilities: float = 0


@app.post("/api/loans")
async def add_loan(loan: LoanCreate):
    """Add a new loan to the portfolio."""
    service = get_portfolio_service()
    result = service.add_loan(loan.model_dump())
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
    """AI assistant for portfolio questions."""
    try:
        # Get portfolio context
        service = get_portfolio_service()
        summary = service.get_portfolio_summary()

        # Build context for AI
        portfolio_context = f"""
Portfolio Summary:
- Total Exposure: ${summary['total_exposure']:,.0f}
- Loan Count: {summary['loan_count']}
- Average PD: {summary['avg_pd']:.2f}%
- Average LGD: {summary['avg_lgd']:.2f}%
- Expected Loss: ${summary['expected_loss']:,.0f}
- Regulatory Capital: ${summary['regulatory_capital']:,.0f}
- Economic Capital (VaR 99.9%): ${summary['economic_capital']:,.0f}
- Current Loans: {summary['current_count']}
- Delinquent Loans: {summary['delinquent_count']}
- Default Loans: {summary['default_count']}
"""

        # Try to use RAG service if available
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "4_endpoints"))
            from serve_rag import query

            result = query({
                "question": request.message,
                "risk_context": {
                    "portfolio_summary": summary,
                    "avg_pd": summary['avg_pd'],
                    "total_exposure": summary['total_exposure'],
                },
            })

            return {
                "message": result.get("answer", "Unable to generate response"),
                "sources": result.get("sources", []),
                "portfolio_context": summary if request.include_portfolio_context else None,
            }

        except Exception as e:
            # Fallback: return portfolio summary as response
            return {
                "message": f"Based on the current portfolio:\n{portfolio_context}\n\nFor your question: '{request.message}'\n\nPlease refer to the portfolio metrics above for insights.",
                "sources": [],
                "portfolio_context": summary if request.include_portfolio_context else None,
            }

    except Exception as e:
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
    import pickle

    base_path = Path(__file__).parent.parent / "data" / "models"

    # Load PD model metrics
    pd_metrics = {"status": "unknown", "auc_roc": None, "gini": None, "ks_statistic": None}
    try:
        pd_path = base_path / "pd" / "pd_model_latest.pkl"
        if pd_path.exists():
            with open(pd_path, 'rb') as f:
                pd_data = pickle.load(f)
                if isinstance(pd_data, dict) and "metrics" in pd_data:
                    pd_metrics = {
                        "status": "healthy",
                        "version": pd_data.get("version", "1.0"),
                        "model_type": pd_data.get("model_type", "unknown"),
                        "trained_at": str(pd_data.get("trained_at", "")),
                        **pd_data["metrics"]
                    }
    except Exception as e:
        pd_metrics["error"] = str(e)

    # Load LGD model metrics
    lgd_metrics = {"status": "unknown", "mse": None, "r2": None}
    try:
        lgd_path = base_path / "lgd" / "lgd_model_latest.pkl"
        if lgd_path.exists():
            with open(lgd_path, 'rb') as f:
                lgd_data = pickle.load(f)
                if isinstance(lgd_data, dict) and "metrics" in lgd_data:
                    lgd_metrics = {
                        "status": "healthy",
                        "version": lgd_data.get("version", "1.0"),
                        "model_type": lgd_data.get("model_type", "unknown"),
                        "trained_at": str(lgd_data.get("trained_at", "")),
                        **lgd_data["metrics"]
                    }
    except Exception as e:
        lgd_metrics["error"] = str(e)

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

"""
API Routes
FastAPI route handlers for the Credit Risk Platform.
"""

from .applications import router as applications_router
from .workflow import router as workflow_router
from .analyst import router as analyst_router
from .decisions import router as decisions_router
from .websocket import router as websocket_router

__all__ = [
    "applications_router",
    "workflow_router",
    "analyst_router",
    "decisions_router",
    "websocket_router",
]

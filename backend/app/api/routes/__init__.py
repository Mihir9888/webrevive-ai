"""API Routes package."""

from app.api.routes.scan import router as scan_router
from app.api.routes.analyze import router as analyze_router
from app.api.routes.refactor import router as refactor_router
from app.api.routes.projects import router as projects_router
from app.api.routes.reports import router as reports_router

__all__ = [
    "scan_router",
    "analyze_router",
    "refactor_router",
    "projects_router",
    "reports_router",
]

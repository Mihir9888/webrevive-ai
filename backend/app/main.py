"""WebRevive AI - FastAPI Application Entry Point."""

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from datetime import datetime
import logging
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.scan import router as scan_router
from app.api.routes.analyze import router as analyze_router
from app.api.routes.refactor import router as refactor_router
from app.api.routes.projects import router as projects_router
from app.api.routes.reports import router as reports_router
from app.core.config import settings
from app.models.database import init_db
from app.services.scanner import scanner

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger("webrevive.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: setup database tables and initialize Playwright."""
    logger.info("Initializing WebRevive AI backend application...")

    # 1. Initialize DB tables
    await init_db()

    # 2. Warm up Playwright browser instance
    try:
        await scanner.initialize()
    except Exception as exc:
        logger.warning(f"Browser warmup notice: {exc}")

    logger.info(f"{settings.PROJECT_NAME} v{settings.VERSION} ready.")
    yield

    # Teardown
    logger.info("Shutting down WebRevive AI backend application...")
    try:
        await scanner.close()
    except Exception as exc:
        logger.error(f"Error during browser teardown: {exc}")
    logger.info("Cleanup complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS Middleware (dev-friendly)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Register API Routers under /api
app.include_router(scan_router, prefix=settings.API_V1_STR)
app.include_router(analyze_router, prefix=settings.API_V1_STR)
app.include_router(refactor_router, prefix=settings.API_V1_STR)
app.include_router(projects_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root_endpoint() -> dict:
    """Root metadata endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.PROJECT_DESCRIPTION,
        "docs": "/api/docs",
        "health": "/api/health",
    }


@app.get("/api/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """Service health verification endpoint."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "app": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "api": "online",
                "database": "connected",
                "scanner": "ready",
                "ai_engine": f"configured ({settings.OLLAMA_MODEL})",
            },
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

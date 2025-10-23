"""
Main FastAPI application with logging, monitoring, and middleware setup.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.auth import router as auth_router
from src.api.v1.notion import router as notion_router
from src.api.v1.persons import router as persons_router
from src.api.v1.activities import router as activities_router
from src.api.v1.admin import router as admin_router
from src.core.config import Config
from src.core.logging import get_logger, setup_logging
from src.db.database import check_db_connection, close_db

config = Config()

setup_logging(
    level="DEBUG" if config.DEBUG else "INFO",
    json_logs=not config.DEBUG,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    logger.info("application_startup", app_name=config.APP_NAME)
    
    # Check database connectivity on startup
    db_connected = await check_db_connection()
    if not db_connected:
        logger.error("database_connection_failed", message="Failed to connect to database on startup")
        raise RuntimeError("Database connection failed")
    
    yield

    
    
    # Close database connections on shutdown
    await close_db()
    logger.info("application_shutdown", app_name=config.APP_NAME)


app = FastAPI(
    title=config.APP_NAME,
    description="FastAPI application with structured logging and monitoring",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": config.APP_NAME}


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint.

    Returns 200 if the service is ready to accept traffic.
    This checks database connectivity and other dependencies.
    """
    db_connected = await check_db_connection()
    if not db_connected:
        return {"status": "not_ready", "service": config.APP_NAME, "database": "disconnected"}
    return {"status": "ready", "service": config.APP_NAME, "database": "connected"}


app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(notion_router, prefix="/api/v1", tags=["Notion"])
app.include_router(persons_router, prefix="/api/v1", tags=["Persons"])
app.include_router(activities_router, prefix="/api/v1", tags=["Activities"])
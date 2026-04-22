import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.database import Base, async_engine
from .core.redis import close_redis
from .core.middleware import TenantMiddleware
from .api import (
    auth,
    users,
    cameras,
    incidents,
    events,
    files,
    folders,
    dashboard,
    roles,
    tenants,
    camera_modules,
    tenant_modules,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("Starting AMS Backend...")

    # Create database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created")

    yield

    # Shutdown
    logger.info("Shutting down AMS Backend...")
    await close_redis()
    await async_engine.dispose()
    logger.info("Cleanup completed")


# Create FastAPI application
app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Access Management System Backend API",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add tenant middleware
app.add_middleware(
    TenantMiddleware,
    exclude_paths=[
        "/health",
        "/",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/tenants",  # Tenant management endpoints
    ],
    tenant_header="X-Tenant",
    tenant_path_param="tenant",
    tenant_query_param="tenant",
    use_subdomain=True,
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.version,
        "environment": settings.environment,
    }


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "AMS Vision Backend API",
        "version": settings.version,
        "docs_url": f"{settings.api_v1_prefix}/docs",
    }


# Include API routers
app.include_router(
    auth.router, prefix=f"{settings.api_v1_prefix}/auth", tags=["Authentication"]
)

app.include_router(
    users.router, prefix=f"{settings.api_v1_prefix}/users", tags=["Users"]
)

app.include_router(
    cameras.router, prefix=f"{settings.api_v1_prefix}/cameras", tags=["Cameras"]
)

app.include_router(
    incidents.router, prefix=f"{settings.api_v1_prefix}/incidents", tags=["Incidents"]
)

app.include_router(
    events.router, prefix=f"{settings.api_v1_prefix}/events", tags=["Events"]
)

app.include_router(
    files.router, prefix=f"{settings.api_v1_prefix}/files", tags=["Files"]
)

app.include_router(
    folders.router, prefix=f"{settings.api_v1_prefix}/folders", tags=["Folders"]
)

app.include_router(
    dashboard.router, prefix=f"{settings.api_v1_prefix}/dashboard", tags=["Dashboard"]
)

app.include_router(
    roles.router, prefix=f"{settings.api_v1_prefix}/roles", tags=["Roles & Permissions"]
)

app.include_router(
    tenants.router, prefix=f"{settings.api_v1_prefix}/tenants", tags=["Tenants"]
)

app.include_router(
    camera_modules.router,
    prefix=f"{settings.api_v1_prefix}/camera-modules",
    tags=["Camera Modules"],
)

app.include_router(
    tenant_modules.router,
    prefix=f"{settings.api_v1_prefix}/tenants",
    tags=["Tenant Modules"],
)

# Frigate webhook integration
from app.api import frigate_webhook

app.include_router(
    frigate_webhook.router,
    prefix=f"{settings.api_v1_prefix}/frigate",
    tags=["Frigate Integration"],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)

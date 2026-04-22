from typing import Optional, Type, TypeVar, Any
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.sql.selectable import Select

from .config import settings

# Import here to avoid circular imports
try:
    from .tenant import tenant_service
except ImportError:
    # During initial import, tenant_service might not be available
    tenant_service = None

# Sync engine for migrations
sync_engine = create_engine(
    settings.database_url.replace("postgresql://", "postgresql://"),
    pool_pre_ping=True,
    echo=settings.debug,
)

# Async engine for the application
async_engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    pool_pre_ping=True,
    echo=settings.debug,
)

# Base declarative model
Base = declarative_base()

# Type variable for model classes
ModelType = TypeVar("ModelType", bound=Base)


class TenantAwareSession(AsyncSession):
    """
    Custom SQLAlchemy session that automatically applies tenant filters to queries.
    This ensures that all queries are filtered by tenant without having to modify existing code.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def execute(self, statement, *args, **kwargs):
        """Override execute to apply tenant filter to queries"""
        # Apply tenant filter to SELECT statements if tenant_id is available
        if tenant_service and hasattr(statement, "is_select") and statement.is_select:
            statement = self._apply_tenant_filter(statement)

        return await super().execute(statement, *args, **kwargs)

    def _apply_tenant_filter(self, statement: Select) -> Select:
        """Apply tenant filter to a SELECT statement"""
        tenant_id = tenant_service.get_tenant_id() if tenant_service else None

        if tenant_id is None:
            # No tenant context, return statement as is
            return statement

        # Check if any of the FROM clauses have a tenant_id column
        for from_clause in statement.froms:
            if hasattr(from_clause, "columns") and hasattr(from_clause.columns, "get"):
                if "tenant_id" in from_clause.columns:
                    # Add tenant filter to the statement
                    return statement.where(from_clause.columns.tenant_id == tenant_id)

        # No tenant_id column found, return statement as is
        return statement


# Session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=TenantAwareSession,  # Use our custom session class
    expire_on_commit=False,
)


# Dependency to get async session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Sync session for migrations and seeding
def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Function to get a model by ID with tenant validation
async def get_object_by_id_with_tenant(
    db: AsyncSession, model: Type[ModelType], id: Any, tenant_id: Optional[int] = None
) -> Optional[ModelType]:
    """
    Get an object by ID with tenant validation.
    If tenant_id is provided, it will be used for validation.
    Otherwise, the current tenant context will be used.
    """
    from sqlalchemy import select

    # Use provided tenant_id or get from context
    if tenant_id is None and tenant_service:
        tenant_id = tenant_service.get_tenant_id()

    # Build query
    query = select(model).where(model.id == id)

    # Add tenant filter if model has tenant_id and tenant_id is available
    if tenant_id is not None and hasattr(model, "tenant_id"):
        query = query.where(model.tenant_id == tenant_id)

    # Execute query
    result = await db.execute(query)
    return result.scalar_one_or_none()

# Multi-Tenant Architecture in AMS Vision Backend

This document describes the multi-tenant architecture implemented in the AMS Vision Backend.

## Overview

The AMS Vision Backend uses a schema-shared multi-tenant architecture, where all tenants share the same database schema but are isolated by a `tenant_id` column in each table. This approach provides good isolation while maintaining simplicity and efficiency.

## Key Components

### 1. Tenant Model

The `Tenant` model is the core of the multi-tenant architecture. It stores information about each tenant, including:

- Basic information (name, slug)
- Status and subscription details
- Contact information
- Tenant-specific settings (as JSON)

```python
class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    status = Column(String(50), default="active")
    subscription_plan = Column(String(50), nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    settings = Column(JSONB, default={})
```

### 2. TenantMixin

The `TenantMixin` is applied to all models that need tenant isolation. It adds a `tenant_id` foreign key and a relationship to the `Tenant` model.

```python
class TenantMixin:
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    # The tenant relationship is defined in each model class
```

### 3. Tenant-Aware Session

The `TenantAwareSession` automatically applies tenant filters to queries, ensuring that all queries are filtered by tenant without having to modify existing code.

```python
class TenantAwareSession(AsyncSession):
    async def execute(self, statement, *args, **kwargs):
        if tenant_service and hasattr(statement, "is_select") and statement.is_select:
            statement = self._apply_tenant_filter(statement)
        return await super().execute(statement, *args, **kwargs)
```

### 4. Tenant Middleware

The `TenantMiddleware` extracts tenant information from the request and sets it in the context. It supports multiple methods for tenant identification:

- HTTP header
- Path parameter
- Query parameter
- Subdomain

```python
class TenantMiddleware:
    def __init__(
        self,
        app,
        exclude_paths: Optional[List[str]] = None,
        tenant_header: str = "X-Tenant",
        tenant_path_param: str = "tenant",
        tenant_query_param: str = "tenant",
        use_subdomain: bool = True,
        subdomain_pattern: str = r"^(?P<tenant>[a-zA-Z0-9-]+)\.",
    ):
        # ...
```

### 5. Tenant Service

The `TenantService` manages tenant context using context variables, ensuring that tenant information is properly isolated between requests.

```python
class TenantService:
    def set_tenant_id(self, tenant_id: int) -> None:
        tenant_id_var.set(tenant_id)
    
    def get_tenant_id(self) -> Optional[int]:
        return tenant_id_var.get()
    
    # ...
```

### 6. Authentication with Tenant Context

The authentication system has been updated to include tenant context in tokens and validation.

```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, tenant_id: Optional[int] = None):
    # ...
    if tenant_id is not None:
        to_encode.update({"tenant_id": tenant_id})
    # ...
```

## Database Schema

The database schema includes a `tenants` table and a `tenant_id` column in all tenant-aware tables:

- users
- cameras
- incidents
- events
- files
- folders
- roles

Each `tenant_id` column is indexed and has a foreign key constraint to the `tenants` table with `ON DELETE CASCADE`.

## API Endpoints

The API includes endpoints for tenant management:

- `POST /api/v1/tenants` - Create a new tenant
- `GET /api/v1/tenants` - List all tenants
- `GET /api/v1/tenants/{tenant_id}` - Get tenant details
- `PUT /api/v1/tenants/{tenant_id}` - Update tenant details
- `DELETE /api/v1/tenants/{tenant_id}` - Delete a tenant
- `GET /api/v1/tenants/by-slug/{slug}` - Get tenant by slug

These endpoints are protected and can only be accessed by superadmin users.

## Tenant Identification

Tenants can be identified in several ways:

1. **HTTP Header**: `X-Tenant: tenant-slug`
2. **Path Parameter**: `/api/v1/resource?tenant=tenant-slug`
3. **Query Parameter**: `/api/v1/tenant/tenant-slug/resource`
4. **Subdomain**: `tenant-slug.example.com`

The middleware tries each method in order and uses the first one that provides a valid tenant.

## Security Considerations

1. **Tenant Isolation**: All queries are automatically filtered by tenant_id
2. **Superadmin Access**: Only superadmin users can manage tenants
3. **Token Validation**: Tokens include tenant_id and are validated against it
4. **Middleware Exclusions**: Some endpoints are excluded from tenant validation

## Usage Examples

### Creating a Tenant

```python
tenant = Tenant(
    name="Example Company",
    slug="example",
    status="active",
    subscription_plan="premium",
    contact_email="admin@example.com"
)
db.add(tenant)
await db.commit()
```

### Creating a User with Tenant

```python
user = User(
    email="user@example.com",
    password_hash=get_password_hash("password"),
    first_name="John",
    last_name="Doe",
    tenant_id=tenant.id
)
db.add(user)
await db.commit()
```

### Querying with Tenant Context

```python
# The tenant_id filter is automatically applied by TenantAwareSession
result = await db.execute(select(User).where(User.email == "user@example.com"))
user = result.scalar_one_or_none()
```

## Migration Guide

To migrate existing data to the multi-tenant architecture:

1. Run the migration script to create the tenants table and add tenant_id columns
2. Create a default tenant
3. Assign all existing records to the default tenant
4. Update your code to use the tenant-aware models and middleware

## Best Practices

1. Always use the tenant-aware session for database operations
2. Use the tenant middleware to extract tenant information from requests
3. Include tenant_id in tokens for authentication
4. Use the tenant service to manage tenant context
5. Test thoroughly to ensure proper tenant isolation


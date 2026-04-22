# Complete Backend Understanding Guide

## 🎯 Purpose of This Guide

This guide is designed to take you from zero knowledge to complete understanding of the AMS Vision Backend. Follow this route step-by-step, reading each file in order, and by the end you'll understand every detail of how the backend works.

---

## 📋 Table of Contents

1. [Start Here: High-Level Overview](#1-start-here-high-level-overview)
2. [Understanding the Project Structure](#2-understanding-the-project-structure)
3. [Core Configuration and Setup](#3-core-configuration-and-setup)
4. [Database Architecture](#4-database-architecture)
5. [Multi-Tenant System](#5-multi-tenant-system)
6. [Authentication & Security](#6-authentication--security)
7. [Domain Models](#7-domain-models)
8. [Data Access Layer (Repositories)](#8-data-access-layer-repositories)
9. [Business Logic Layer (Services)](#9-business-logic-layer-services)
10. [API Layer](#10-api-layer)
11. [External Integrations](#11-external-integrations)
12. [Putting It All Together](#12-putting-it-all-together)

---

## 1. Start Here: High-Level Overview

### Step 1.1: Read the README
**File:** `README.md`

**What to understand:**
- What the backend does (Access Management System for camera monitoring)
- Main technologies used (FastAPI, PostgreSQL, Redis)
- Quick start instructions
- Basic API endpoints overview

**Key takeaways:**
- This is a **B2B multi-tenant** system for managing cameras, events, incidents, and files
- Uses **FastAPI** (modern async Python web framework)
- **PostgreSQL** for data storage
- **Redis** for caching
- **JWT** for authentication
- **MinIO** for object storage (files)

### Step 1.2: Understand the Project Structure
**File:** `PROJECT_STRUCTURE.md`

**What to understand:**
- How the codebase is organized
- What each folder contains
- The relationship between different components

**Key takeaways:**
- `app/` - Main application code
  - `api/` - HTTP endpoints (routes)
  - `core/` - Core infrastructure (config, database, security)
  - `models/` - Database models (SQLAlchemy)
  - `schemas/` - Request/response validation (Pydantic)
  - `repositories/` - Data access layer (DDD pattern)
  - `services/` - Business logic layer
- `alembic/` - Database migrations
- `docs/` - Documentation

### Step 1.3: Check Dependencies
**File:** `requirements.txt`

**What to understand:**
- What external libraries are used
- Why each library is needed

**Key libraries:**
- `fastapi` - Web framework
- `sqlalchemy` - ORM for database
- `alembic` - Database migrations
- `asyncpg` - PostgreSQL async driver
- `redis` - Redis client
- `python-jose` - JWT handling
- `passlib` - Password hashing (Argon2/bcrypt)
- `pydantic` - Data validation
- `minio` - Object storage client

---

## 2. Understanding the Project Structure

### Step 2.1: The Application Entry Point
**File:** `app/main.py`

**What to understand:**
- How the FastAPI app is initialized
- What middleware is configured
- How routes are registered
- Application lifecycle (startup/shutdown)

**Key concepts:**
1. **FastAPI Application Creation:**
   ```python
   app = FastAPI(
       title=settings.project_name,
       version=settings.version,
       description="Access Management System Backend API",
       ...
   )
   ```

2. **Middleware Stack:**
   - CORS middleware (cross-origin requests)
   - Tenant middleware (multi-tenant isolation)

3. **Route Registration:**
   - All API routes are included with prefixes
   - Routes are organized by domain (auth, users, cameras, etc.)

4. **Lifespan Events:**
   - Startup: Create database tables
   - Shutdown: Close connections, cleanup

**What happens when a request comes in:**
1. Request hits FastAPI
2. CORS middleware processes it
3. Tenant middleware extracts tenant info
4. Route handler processes request
5. Response is returned

---

## 3. Core Configuration and Setup

### Step 3.1: Application Configuration
**File:** `app/core/config.py`

**What to understand:**
- How settings are loaded (environment variables)
- What configuration options exist
- How tenant-specific settings work

**Key settings:**
- **Database:** Connection URL, pool settings
- **Redis:** Cache connection
- **Security:** JWT secret, token expiration
- **File Upload:** Max size, allowed extensions
- **MinIO:** Object storage configuration
- **Frigate:** NVR integration URL
- **CORS:** Allowed origins

**Important concept: `TenantSettings`**
- Allows per-tenant configuration overrides
- Merges tenant-specific settings with global settings
- Used for tenant customization

### Step 3.2: Database Connection
**File:** `app/core/database.py`

**What to understand:**
- How database connections are managed
- Async vs sync engines
- Tenant-aware session implementation
- Database dependency injection

**Key concepts:**

1. **Two Engines:**
   - `sync_engine` - For migrations (Alembic)
   - `async_engine` - For application (async operations)

2. **TenantAwareSession:**
   - Automatically filters queries by `tenant_id`
   - Ensures data isolation between tenants
   - Transparent to application code

3. **Session Management:**
   - `get_db()` - Async dependency for routes
   - Automatically closes sessions after request
   - Uses context managers for safety

**How tenant filtering works:**
```python
# When you query:
result = await db.execute(select(User).where(User.email == "user@example.com"))

# TenantAwareSession automatically adds:
# WHERE User.tenant_id == current_tenant_id
```

### Step 3.3: Redis Connection
**File:** `app/core/redis.py`

**What to understand:**
- How Redis is connected
- Connection pooling
- Cache management

**Usage:**
- Caching feature flags
- Session storage
- Performance optimization

---

## 4. Database Architecture

### Step 4.1: Base Model and Tenant Mixin
**File:** `app/models/base.py`

**What to understand:**
- How all models inherit from `Base`
- What `TenantMixin` does
- Why tenant isolation is important

**Key concept: `TenantMixin`**
- Adds `tenant_id` column to all models
- Ensures all data is tenant-scoped
- Provides foreign key to `tenants` table

**Every tenant-aware model:**
```python
class SomeModel(Base, TenantMixin):
    # Automatically has tenant_id column
    # Automatically has tenant relationship
```

### Step 4.2: Core Domain Models

#### Step 4.2.1: Tenant Model
**File:** `app/models/tenant.py`

**What to understand:**
- What a tenant represents (a company/organization)
- Tenant fields (name, slug, status, settings)
- Relationships to other models

**Key fields:**
- `slug` - Unique identifier for routing (e.g., "acme-corp")
- `status` - active, inactive, trial
- `settings` - JSONB for tenant-specific config
- Relationships to users, cameras, events, etc.

#### Step 4.2.2: User Model
**File:** `app/models/user.py`

**What to understand:**
- User authentication fields
- Role-based access control
- Tenant relationship
- Permission system

**Key fields:**
- `email` - Unique identifier
- `password_hash` - Argon2 hashed password
- `role` - Legacy role field (backward compatibility)
- `role_id` - New RBAC role reference
- `is_superadmin` - System-wide admin flag
- `tenant_id` - Which tenant the user belongs to

**Relationships:**
- `tenant` - Belongs to a tenant
- `role_obj` - Has a role
- `direct_permissions` - Direct permission grants

#### Step 4.2.3: Role and Permission Models
**Files:** `app/models/role.py`, `app/models/permission.py`, `app/models/user_permission.py`

**What to understand:**
- Hierarchical role system
- Permission-based access control
- How roles and permissions work together

**Role Hierarchy:**
- Roles can have parent roles
- Permissions are inherited from parent roles
- `level` and `path` fields track hierarchy

**Permission System:**
- Permissions are `resource:action` pairs (e.g., "cameras:create")
- Roles have many permissions
- Users can have direct permissions (overrides role)

#### Step 4.2.4: Camera Model
**File:** `app/models/camera.py`

**What to understand:**
- Camera entity structure
- Status management
- Zone configuration (for Frigate)
- Relationships

**Key fields:**
- `name` - Camera identifier
- `location` - Physical location
- `status` - active, inactive, maintenance
- `stream_url` - Video stream URL
- `zones` - JSONB field for Frigate zone definitions

#### Step 4.2.5: Event Model
**File:** `app/models/event.py`

**What to understand:**
- Event structure
- Frigate integration fields
- Event types and metadata

**Key fields:**
- `event_type` - Type of event (motion, person, alarm, etc.)
- `frigate_event_id` - Link to Frigate event
- `object_type` - Detected object (person, car, etc.)
- `confidence` - Detection confidence score
- `snapshot_url` - Event snapshot image
- `clip_url` - Event video clip
- `metadata` - JSONB for additional data

#### Step 4.2.6: File and Folder Models
**Files:** `app/models/file.py`, `app/models/folder.py`

**What to understand:**
- File storage structure
- Folder hierarchy
- MinIO integration
- Tenant isolation

**Key concepts:**
- Files stored in MinIO object storage
- Folders provide organization
- Both are tenant-scoped

#### Step 4.2.7: Camera Modules System
**Files:** 
- `app/models/camera_feature.py`
- `app/models/camera_module.py`
- `app/models/tenant_camera_module.py`
- `app/models/tenant_feature_override.py`

**What to understand:**
- B2B feature management system
- Atomic features vs business modules
- Tenant module assignments
- Feature overrides

**Architecture:**
1. **CameraFeature** - Atomic feature (e.g., "motion_detection", "face_recognition")
2. **CameraModule** - Business module (e.g., "Hotel", "Cafe") containing multiple features
3. **TenantCameraModule** - Links tenants to modules (enabled/disabled)
4. **TenantFeatureOverride** - Per-tenant feature overrides (force enable/disable)

**Use case:**
- Tenant "Hotel A" gets "Hotel" module → gets all hotel features
- Tenant "Cafe B" gets "Cafe" module → gets cafe-specific features
- Tenant can override individual features (enable/disable)

### Step 4.3: Database Migrations
**Directory:** `alembic/versions/`

**What to understand:**
- How schema changes are versioned
- Migration workflow
- How to read migration files

**Key migrations:**
- `2242e527ac00_initial_migration.py` - Initial schema
- `add_tenant_table.py` - Multi-tenant support
- `2008b7b7815e_add_rbac_tables_and_hierarchical_roles.py` - RBAC system
- `a1b2c3d4e5f6_add_camera_modules_system.py` - Camera modules
- `f8a9b2c3d4e5_add_frigate_fields_to_events.py` - Frigate integration

**How migrations work:**
1. Create migration: `alembic revision --autogenerate -m "description"`
2. Review generated migration
3. Apply: `alembic upgrade head`
4. Rollback: `alembic downgrade -1`

---

## 5. Multi-Tenant System

### Step 5.1: Multi-Tenant Architecture Documentation
**File:** `docs/multi_tenant_architecture.md`

**What to understand:**
- Schema-shared multi-tenancy approach
- How tenant isolation works
- Tenant identification methods

**Key concepts:**
- All tenants share the same database schema
- Data is isolated by `tenant_id` column
- Each table has `tenant_id` foreign key
- Queries are automatically filtered by tenant

### Step 5.2: Tenant Service
**File:** `app/core/tenant.py`

**What to understand:**
- How tenant context is managed
- Context variables for tenant info
- Tenant service methods

**Key methods:**
- `set_tenant_id()` - Set current tenant
- `get_tenant_id()` - Get current tenant
- `get_tenant_by_slug()` - Lookup tenant by slug

**Context Variables:**
- `tenant_id_var` - Current tenant ID
- `tenant_slug_var` - Current tenant slug
- `tenant_settings_var` - Tenant-specific settings

**Why context variables?**
- Thread-safe (async-safe)
- Isolated per request
- No need to pass tenant_id everywhere

### Step 5.3: Tenant Middleware
**File:** `app/core/middleware.py`

**What to understand:**
- How tenant is extracted from requests
- Multiple identification methods
- Tenant validation

**Tenant Identification Methods (in order):**
1. **HTTP Header:** `X-Tenant: tenant-slug`
2. **Path Parameter:** `/api/v1/tenant/tenant-slug/resource`
3. **Query Parameter:** `/api/v1/resource?tenant=tenant-slug`
4. **Subdomain:** `tenant-slug.example.com`

**Flow:**
1. Request comes in
2. Middleware extracts tenant slug
3. Validates tenant exists and is active
4. Sets tenant context
5. Request continues
6. Context is cleared after request

**Excluded paths:**
- `/health`
- `/docs`
- `/auth/login`
- `/auth/register`
- `/tenants` (tenant management)

---

## 6. Authentication & Security

### Step 6.1: Security Module
**File:** `app/core/security.py`

**What to understand:**
- JWT token creation and validation
- Password hashing (Argon2)
- Password migration (bcrypt → Argon2)
- Current user dependency

**Key functions:**

1. **Password Hashing:**
   ```python
   get_password_hash(password)  # Returns Argon2 hash
   verify_password(plain, hash)  # Verifies password
   needs_rehash(hash)  # Checks if migration needed
   ```

2. **JWT Tokens:**
   ```python
   create_access_token(data, tenant_id)  # Short-lived token
   create_refresh_token(data, tenant_id)  # Long-lived token
   verify_token(token, type)  # Validates token
   ```

3. **Current User:**
   ```python
   get_current_user()  # FastAPI dependency
   # Extracts user from JWT token
   # Validates tenant_id matches
   # Returns User object
   ```

**Password Migration:**
- Old passwords use bcrypt
- New passwords use Argon2
- Automatic migration on login
- No 72-byte limit (Argon2 advantage)

**Token Structure:**
```json
{
  "sub": "user_id",
  "tenant_id": 123,
  "exp": 1234567890,
  "type": "access"
}
```

### Step 6.2: Authentication Endpoints
**File:** `app/api/auth.py`

**What to understand:**
- Login flow
- Registration flow
- Token refresh
- Password migration

**Login Flow:**
1. User sends email + password
2. Find user by email
3. Verify password
4. Check if active
5. Migrate password if needed (bcrypt → Argon2)
6. Create JWT tokens (with tenant_id)
7. Return tokens

**Registration Flow:**
1. User sends registration data
2. Validate tenant (from context or parameter)
3. Check email not taken
4. Assign default role ("viewer")
5. Hash password (Argon2)
6. Create user
7. Return user (no tokens - must login)

**Security measures:**
- No `tenant_id` in registration body (security)
- No role selection in registration (security)
- Default role is "viewer" (lowest privilege)
- Superadmin cannot be created via registration

### Step 6.3: Permissions System
**File:** `app/core/permissions.py`

**What to understand:**
- Permission checking
- Role-based dependencies
- Permission service

**Permission Checkers:**
- `PermissionChecker` - Check single permission
- `MultiPermissionChecker` - Check multiple permissions
- `ResourceOwnershipChecker` - Check ownership + permission

**Usage in routes:**
```python
@router.get("/cameras")
async def get_cameras(
    current_user: User = Depends(RequireCameraRead)
):
    # User must have "cameras:read" permission
    ...
```

**Permission format:**
- `resource:action` (e.g., "cameras:create", "users:delete")
- Hierarchical roles inherit permissions
- Direct user permissions override role permissions

---

## 7. Domain Models

### Step 7.1: Understanding Model Relationships

**Read these files in order:**
1. `app/models/__init__.py` - See all models imported
2. `app/models/tenant.py` - Central model
3. `app/models/user.py` - User model
4. `app/models/role.py` - Role model
5. `app/models/permission.py` - Permission model
6. `app/models/camera.py` - Camera model
7. `app/models/event.py` - Event model
8. `app/models/file.py` - File model
9. `app/models/folder.py` - Folder model
10. `app/models/incident.py` - Incident model
11. `app/models/audit_log.py` - Audit logging

**What to understand:**
- Foreign key relationships
- Many-to-many relationships
- Back references
- Cascade behaviors

**Key relationships:**
- User → Tenant (many-to-one)
- User → Role (many-to-one)
- Role → Permissions (many-to-many)
- User → Permissions (many-to-many via UserPermission)
- Camera → Tenant (many-to-one)
- Event → Camera (many-to-one)
- Event → Tenant (many-to-one)
- File → Folder (many-to-one)
- File → Tenant (many-to-one)

---

## 8. Data Access Layer (Repositories)

### Step 8.1: Repository Pattern
**Directory:** `app/repositories/`

**What to understand:**
- Why repositories (DDD pattern)
- How repositories abstract database access
- Standard repository methods

**Repository Pattern Benefits:**
- Separation of concerns
- Testability (can mock repositories)
- Consistent data access
- Business logic stays in services

### Step 8.2: Example Repository
**File:** `app/repositories/role.py`

**What to understand:**
- Standard CRUD operations
- Complex queries
- Relationship handling
- Cache invalidation

**Key methods:**
- `get()` - Get by ID
- `get_by_name()` - Get by name (with tenant filter)
- `get_multi()` - List with pagination
- `create()` - Create new
- `update()` - Update existing
- `delete()` - Delete
- `get_hierarchy()` - Get role hierarchy
- `get_inherited_permissions()` - Get all permissions (including inherited)

**What to notice:**
- All methods are async
- Tenant filtering is explicit where needed
- Eager loading for relationships (`selectinload`)
- Cache invalidation after updates

### Step 8.3: Other Repositories
**Files:**
- `app/repositories/permission.py`
- `app/repositories/camera_feature.py`
- `app/repositories/camera_module.py`
- `app/repositories/tenant_module.py`

**What to understand:**
- Each repository handles one domain entity
- Consistent interface across repositories
- Specialized methods for domain logic

---

## 9. Business Logic Layer (Services)

### Step 9.1: Service Pattern
**Directory:** `app/services/`

**What to understand:**
- Why services exist
- How services use repositories
- Business logic vs data access

**Service Responsibilities:**
- Complex business logic
- Orchestrating multiple repositories
- Caching strategies
- External API calls
- Data transformation

### Step 9.2: Camera Feature Service
**File:** `app/services/camera_feature_service.py`

**What to understand:**
- Feature checking logic
- Redis caching
- Override precedence
- Cache invalidation

**Feature Checking Logic:**
1. Check feature override first (highest priority)
2. If no override, check if feature is in any enabled module
3. Cache results in Redis (5 min TTL)
4. Invalidate cache on changes

**Key methods:**
- `has_feature()` - Check if tenant has feature
- `get_tenant_features()` - Get all enabled features
- `get_tenant_feature_codes()` - Get feature codes only
- `invalidate_tenant_cache()` - Clear cache

### Step 9.3: Frigate Event Service
**File:** `app/services/frigate_event_service.py`

**What to understand:**
- How Frigate events are processed
- Camera name mapping
- Event creation/update logic
- URL building

**Event Processing Flow:**
1. Receive webhook from Frigate
2. Extract camera name from payload
3. Find camera in database by name
4. Extract event data (type, object, confidence, etc.)
5. Build snapshot/clip URLs
6. Create or update event in database
7. Link to camera and tenant

**Key methods:**
- `process_frigate_event()` - Main processing method
- `find_camera_by_name()` - Map Frigate camera name to DB camera
- `find_existing_event()` - Check for duplicate events

### Step 9.4: Other Services
**Files:**
- `app/services/folder_service.py` - Folder hierarchy management
- `app/services/audit_service.py` - Audit logging

---

## 10. API Layer

### Step 10.1: Request/Response Schemas
**Directory:** `app/schemas/`

**What to understand:**
- Pydantic validation
- Request vs response schemas
- Schema inheritance

**Schema Types:**
- `*Base` - Base fields shared by create/update
- `*Create` - Fields for creation (includes password, etc.)
- `*Update` - Fields for updates (all optional)
- `*Response` - Fields returned to client (excludes sensitive data)

**Example:** `app/schemas/user.py`
- `UserBase` - email, first_name, last_name
- `UserCreate` - extends Base + password
- `UserUpdate` - all fields optional
- `UserResponse` - extends Base + id, role, created_at (no password)

### Step 10.2: API Routes Overview
**Directory:** `app/api/`

**Read these files in order:**

#### Step 10.2.1: Authentication
**File:** `app/api/auth.py`

**Endpoints:**
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user
- `PUT /auth/me` - Update current user

**What to understand:**
- Token-based authentication
- Registration security measures
- Password migration on login

#### Step 10.2.2: Users
**File:** `app/api/users.py`

**Endpoints:**
- `GET /users` - List users (paginated, filtered)
- `POST /users` - Create user (admin only)
- `GET /users/{id}` - Get user details
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user
- `PUT /users/{id}/role` - Change user role

**What to understand:**
- Permission-based access control
- Tenant filtering
- User management operations

#### Step 10.2.3: Cameras
**File:** `app/api/cameras.py`

**Endpoints:**
- `GET /cameras` - List cameras
- `POST /cameras` - Create camera
- `GET /cameras/{id}` - Get camera details
- `PUT /cameras/{id}` - Update camera
- `DELETE /cameras/{id}` - Delete camera
- `PUT /cameras/{id}/status` - Update status

**What to understand:**
- Camera CRUD operations
- Status management
- Zone configuration

#### Step 10.2.4: Events
**File:** `app/api/events.py`

**Endpoints:**
- `GET /events` - List events (filtered by type, camera, date, object_type)
- `GET /events/{id}` - Get event details
- `POST /events` - Create event (manual)
- `PUT /events/{id}` - Update event
- `DELETE /events/{id}` - Delete event

**What to understand:**
- Event filtering and search
- Frigate integration fields
- Tenant isolation

#### Step 10.2.5: Files
**File:** `app/api/files.py`

**Endpoints:**
- `GET /files` - List files
- `POST /files/upload` - Upload file to MinIO
- `GET /files/{id}` - Download file
- `GET /files/{id}/metadata` - Get file metadata
- `DELETE /files/{id}` - Delete file
- `GET /files/{id}/download-url` - Get presigned URL
- `PUT /files/{id}/move` - Move file to folder

**What to understand:**
- MinIO integration
- Presigned URLs for secure access
- File validation (size, type)
- Tenant isolation

#### Step 10.2.6: Folders
**File:** `app/api/folders.py`

**Endpoints:**
- `GET /folders` - List folders (tree structure)
- `POST /folders` - Create folder
- `GET /folders/{id}` - Get folder details
- `PUT /folders/{id}` - Update folder
- `DELETE /folders/{id}` - Delete folder
- `GET /folders/{id}/files` - Get files in folder

**What to understand:**
- Folder hierarchy
- Tree structure building
- Cascade operations

#### Step 10.2.7: Roles & Permissions
**File:** `app/api/roles.py`

**Endpoints:**
- `GET /roles` - List roles
- `POST /roles` - Create role
- `GET /roles/{id}` - Get role with permissions
- `PUT /roles/{id}` - Update role
- `DELETE /roles/{id}` - Delete role
- `POST /roles/{id}/permissions` - Assign permission
- `DELETE /roles/{id}/permissions/{perm_id}` - Remove permission

**What to understand:**
- Role hierarchy management
- Permission assignment
- Cache invalidation

#### Step 10.2.8: Tenants
**File:** `app/api/tenants.py`

**Endpoints:**
- `GET /tenants` - List tenants (superadmin only)
- `POST /tenants` - Create tenant (superadmin only)
- `GET /tenants/{id}` - Get tenant details
- `PUT /tenants/{id}` - Update tenant
- `DELETE /tenants/{id}` - Delete tenant
- `GET /tenants/by-slug/{slug}` - Get tenant by slug

**What to understand:**
- Tenant management
- Superadmin-only access
- Tenant settings

#### Step 10.2.9: Camera Modules
**File:** `app/api/camera_modules.py`

**Endpoints:**
- `GET /camera-modules` - List all modules
- `POST /camera-modules` - Create module
- `GET /camera-modules/{code}` - Get module with features
- `PUT /camera-modules/{code}` - Update module
- `DELETE /camera-modules/{code}` - Delete module
- `POST /camera-modules/{code}/features` - Assign feature to module
- `DELETE /camera-modules/{code}/features/{feature_code}` - Remove feature

**What to understand:**
- Module management
- Feature assignment
- B2B feature system

#### Step 10.2.10: Tenant Modules
**File:** `app/api/tenant_modules.py`

**Endpoints:**
- `GET /tenants/{tenant_id}/modules` - Get tenant's modules
- `POST /tenants/{tenant_id}/modules` - Assign module to tenant
- `DELETE /tenants/{tenant_id}/modules/{module_code}` - Remove module
- `GET /tenants/{tenant_id}/features` - Get tenant's enabled features
- `POST /tenants/{tenant_id}/features/override` - Create feature override
- `DELETE /tenants/{tenant_id}/features/override/{feature_code}` - Remove override

**What to understand:**
- Tenant-module assignments
- Feature overrides
- Feature checking logic

#### Step 10.2.11: Dashboard
**File:** `app/api/dashboard.py`

**Endpoints:**
- `GET /dashboard/stats` - Overall statistics
- `GET /dashboard/incidents/summary` - Incident summaries
- `GET /dashboard/cameras/summary` - Camera status summary

**What to understand:**
- Aggregated statistics
- Tenant-scoped data
- Performance considerations

#### Step 10.2.12: Frigate Webhook
**File:** `app/api/frigate_webhook.py`

**Endpoints:**
- `POST /frigate/webhook` - Receive Frigate events
- `GET /frigate/health` - Health check

**What to understand:**
- Webhook processing
- Event creation from external system
- Camera name mapping

### Step 10.3: Common Patterns in API Routes

**What to notice across all routes:**

1. **Dependencies:**
   ```python
   db: AsyncSession = Depends(get_db)
   current_user: User = Depends(get_current_user)
   ```

2. **Permission Checks:**
   ```python
   current_user: User = Depends(RequireCameraRead)
   ```

3. **Tenant Filtering:**
   ```python
   query = select(Camera).where(Camera.tenant_id == current_user.tenant_id)
   ```

4. **Error Handling:**
   ```python
   if not resource:
       raise HTTPException(status_code=404, detail="Not found")
   ```

5. **Response Models:**
   ```python
   @router.get("/", response_model=List[CameraResponse])
   ```

---

## 11. External Integrations

### Step 11.1: MinIO Integration
**File:** `app/core/minio_client.py`

**What to understand:**
- Object storage setup
- Bucket management
- Presigned URL generation
- File upload/download

**Key concepts:**
- MinIO is S3-compatible object storage
- Files stored in buckets
- Presigned URLs for secure temporary access
- Tenant isolation via folder prefixes

### Step 11.2: Frigate Integration
**Files:**
- `app/api/frigate_webhook.py`
- `app/services/frigate_event_service.py`
- `app/schemas/frigate_event.py`

**What to understand:**
- Frigate is an NVR (Network Video Recorder)
- Webhook-based event delivery
- Camera name mapping
- Event processing pipeline

**Flow:**
1. Frigate detects motion/person/etc.
2. Frigate sends webhook to `/frigate/webhook`
3. Service processes webhook
4. Finds camera by name
5. Creates/updates event in database
6. Links to camera and tenant

---

## 12. Putting It All Together

### Step 12.1: Complete Request Flow

**Example: Get user's cameras**

1. **Request arrives:**
   ```
   GET /api/v1/cameras
   Headers: Authorization: Bearer <token>
   ```

2. **Middleware processes:**
   - CORS middleware checks origin
   - Tenant middleware extracts tenant (from token or header)
   - Sets tenant context

3. **Route handler:**
   ```python
   @router.get("/cameras")
   async def get_cameras(
       current_user: User = Depends(get_current_user),
       db: AsyncSession = Depends(get_db)
   ):
   ```

4. **Authentication:**
   - `get_current_user` extracts token
   - Validates token
   - Finds user in database
   - Validates tenant_id matches
   - Returns User object

5. **Database query:**
   ```python
   query = select(Camera).where(Camera.tenant_id == current_user.tenant_id)
   result = await db.execute(query)
   cameras = result.scalars().all()
   ```

6. **Response:**
   - Serialize cameras using `CameraResponse` schema
   - Return JSON response

### Step 12.2: Complete Registration Flow

1. **Request:**
   ```
   POST /api/v1/auth/register
   Body: { email, password, first_name, last_name }
   Query: ?tenant=acme-corp
   ```

2. **Middleware:**
   - Extracts tenant from query parameter
   - Validates tenant exists and is active
   - Sets tenant context

3. **Route handler:**
   ```python
   @router.post("/register")
   async def register(user_data: UserCreate, ...):
   ```

4. **Validation:**
   - Check email not taken
   - Validate password strength
   - Get tenant from context

5. **User creation:**
   - Hash password (Argon2)
   - Assign default role ("viewer")
   - Create user with tenant_id
   - Save to database

6. **Response:**
   - Return user (without password)

### Step 12.3: Complete Event Processing Flow

1. **Frigate detects person:**
   - Frigate sends webhook to backend

2. **Webhook received:**
   ```
   POST /api/v1/frigate/webhook
   Body: { type: "new", camera: "entrance", ... }
   ```

3. **Service processes:**
   - Extract camera name
   - Find camera in database
   - Extract event data
   - Build URLs for snapshot/clip
   - Create event record

4. **Event stored:**
   - Linked to camera
   - Linked to tenant
   - Available via API

5. **Frontend can query:**
   ```
   GET /api/v1/events?object_type=person&camera_id=123
   ```

---

## 🎓 Understanding Checklist

After reading this guide, you should understand:

- [ ] **Architecture:** How the backend is structured (layers, patterns)
- [ ] **Multi-tenancy:** How tenant isolation works
- [ ] **Authentication:** How JWT and password hashing work
- [ ] **Database:** How models relate and how queries work
- [ ] **Repositories:** How data access is abstracted
- [ ] **Services:** How business logic is organized
- [ ] **API:** How endpoints are structured and secured
- [ ] **Integrations:** How MinIO and Frigate integrate
- [ ] **Security:** How permissions and tenant isolation protect data
- [ ] **Features:** How the camera modules system works

---

## 🔍 Next Steps

1. **Run the application:**
   ```bash
   docker-compose up -d
   ```

2. **Explore the API:**
   - Visit http://localhost:8000/api/v1/docs
   - Try endpoints with Swagger UI

3. **Read the code:**
   - Start with a simple endpoint (e.g., `/health`)
   - Trace through the code
   - Understand each layer

4. **Make changes:**
   - Add a new endpoint
   - Add a new model
   - Add a new service

5. **Debug:**
   - Add logging
   - Use debugger
   - Check database queries

---

## 📚 Additional Resources

- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **SQLAlchemy Documentation:** https://docs.sqlalchemy.org/
- **Pydantic Documentation:** https://docs.pydantic.dev/
- **Alembic Documentation:** https://alembic.sqlalchemy.org/
- **Frigate Documentation:** https://docs.frigate.video/

---

## 💡 Key Takeaways

1. **Layered Architecture:**
   - API Layer (routes) → Service Layer (business logic) → Repository Layer (data access) → Database

2. **Multi-Tenancy:**
   - All data is tenant-scoped via `tenant_id`
   - Middleware automatically sets tenant context
   - Queries are automatically filtered

3. **Security:**
   - JWT tokens with tenant_id
   - Permission-based access control
   - Password hashing with Argon2
   - Automatic password migration

4. **DDD Patterns:**
   - Repositories for data access
   - Services for business logic
   - Clear separation of concerns

5. **External Integrations:**
   - MinIO for file storage
   - Frigate for NVR events
   - Redis for caching

---

**Congratulations!** You now have a complete understanding of the AMS Vision Backend. 🎉


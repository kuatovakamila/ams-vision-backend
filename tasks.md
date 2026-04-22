# RBAC + UBAC Implementation Tasks

## Story Point Estimation: **13-21 Points**

**Difficulty Level: Medium-High**

The current codebase has basic role-based access control (3 roles: admin, operator, viewer) with hardcoded permission checks. Implementing a flexible hierarchical RBAC+UBAC system will require significant refactoring while maintaining existing functionality.

## Current State Analysis

### ✅ What's Already Implemented
- Basic JWT authentication with refresh tokens
- Three user roles: `admin`, `operator`, `viewer`
- Simple role checks: `require_admin()`, `require_operator_or_admin()`
- User model with role field
- Protected endpoints with basic permission validation

### ❌ What's Missing for Full RBAC+UBAC
- Hierarchical role structure
- Granular permissions system
- Resource-based access control
- User-specific permissions (UBAC)
- Permission inheritance
- Dynamic permission checking
- Audit logging for access control

---

## Implementation Plan

### Phase 1: Core RBAC Foundation (5-8 story points)

#### Task 1.1: Create Permission and Role Models
**Points: 2** | **Priority: High**

Create new database models for a flexible permission system:

```python
# app/models/permission.py
class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g., "cameras:read"
    resource = Column(String(50), nullable=False)           # e.g., "cameras"
    action = Column(String(50), nullable=False)             # e.g., "read", "write", "delete"
    description = Column(String(255))

# app/models/role.py  
class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(String(255))
    parent_id = Column(Integer, ForeignKey("roles.id"))     # For hierarchy
    level = Column(Integer, default=0)                      # Hierarchy level
    is_active = Column(Boolean, default=True)
    
    # Relationships
    parent = relationship("Role", remote_side=[id])
    children = relationship("Role")
    permissions = relationship("Permission", secondary="role_permissions")

# app/models/role_permission.py
class RolePermission(Base):
    __tablename__ = "role_permissions"
    
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)
```

#### Task 1.2: Update User Model for RBAC
**Points: 1** | **Priority: High**

```python
# Update app/models/user.py
class User(Base):
    # ... existing fields ...
    role_id = Column(Integer, ForeignKey("roles.id"))  # Replace role string
    
    # Relationships  
    role = relationship("Role", back_populates="users")
    user_permissions = relationship("Permission", secondary="user_permissions")
```

#### Task 1.3: Create Database Migration
**Points: 1** | **Priority: High**

```bash
# Create migration for new tables
alembic revision --autogenerate -m "Add RBAC tables and hierarchical roles"
```

#### Task 1.4: Seed Default Roles and Permissions
**Points: 1** | **Priority: High**

Create comprehensive permission seeding with hierarchical roles:

```python
# app/seed_rbac.py
ROLES_HIERARCHY = {
    "super_admin": {"level": 0, "parent": None},
    "admin": {"level": 1, "parent": "super_admin"}, 
    "operator": {"level": 2, "parent": "admin"},
    "viewer": {"level": 3, "parent": "operator"}
}

PERMISSIONS = [
    # Users
    {"name": "users:read", "resource": "users", "action": "read"},
    {"name": "users:write", "resource": "users", "action": "write"},
    {"name": "users:delete", "resource": "users", "action": "delete"},
    
    # Cameras  
    {"name": "cameras:read", "resource": "cameras", "action": "read"},
    {"name": "cameras:write", "resource": "cameras", "action": "write"},
    {"name": "cameras:delete", "resource": "cameras", "action": "delete"},
    
    # Incidents
    {"name": "incidents:read", "resource": "incidents", "action": "read"},
    {"name": "incidents:write", "resource": "incidents", "action": "write"},
    {"name": "incidents:delete", "resource": "incidents", "action": "delete"},
    
    # Files
    {"name": "files:read", "resource": "files", "action": "read"},
    {"name": "files:write", "resource": "files", "action": "write"},
    {"name": "files:delete", "resource": "files", "action": "delete"},
    
    # Dashboard & Reports
    {"name": "dashboard:read", "resource": "dashboard", "action": "read"},
    {"name": "reports:read", "resource": "reports", "action": "read"},
    {"name": "reports:export", "resource": "reports", "action": "export"},
]
```

### Phase 2: Permission System Core (3-5 story points)

#### Task 2.1: Create Permission Service
**Points: 2** | **Priority: High**

```python
# app/core/permissions.py
from typing import List, Set
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db

class PermissionService:
    @staticmethod
    async def get_user_permissions(user_id: int, db: AsyncSession) -> Set[str]:
        """Get all permissions for a user (role + individual permissions)"""
        # Get role permissions with inheritance
        # Get user-specific permissions
        # Return combined set
        
    @staticmethod  
    async def has_permission(user_id: int, permission: str, db: AsyncSession) -> bool:
        """Check if user has specific permission"""
        
    @staticmethod
    async def has_resource_access(user_id: int, resource: str, action: str, db: AsyncSession) -> bool:
        """Check if user can perform action on resource"""
        
    @staticmethod
    async def get_role_hierarchy_permissions(role_id: int, db: AsyncSession) -> Set[str]:
        """Get permissions including parent role permissions"""
```

#### Task 2.2: Create Permission Decorators
**Points: 2** | **Priority: High**

```python
# app/core/auth_decorators.py
from functools import wraps
from fastapi import Depends, HTTPException, status

def require_permission(permission: str):
    """Decorator to require specific permission"""
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        if not await PermissionService.has_permission(current_user.id, permission, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}"
            )
        return current_user
    return dependency

def require_resource_access(resource: str, action: str):
    """Decorator to require resource-action access"""
    # Similar implementation for resource-based access

def require_any_permission(*permissions: str):
    """Decorator to require any of the listed permissions"""
    
def require_all_permissions(*permissions: str):  
    """Decorator to require all listed permissions"""
```

### Phase 3: UBAC Implementation (2-3 story points)

#### Task 3.1: User-Specific Permissions Model
**Points: 1** | **Priority: Medium**

```python
# app/models/user_permission.py
class UserPermission(Base):
    __tablename__ = "user_permissions"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)
    granted_by = Column(Integer, ForeignKey("users.id"))
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
```

#### Task 3.2: Resource Ownership Model
**Points: 1** | **Priority: Medium**

```python
# Add ownership tracking to existing models
class Camera(Base):
    # ... existing fields ...
    created_by = Column(Integer, ForeignKey("users.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"))  # Who manages this camera
    
class Incident(Base):  
    # ... existing fields ...
    # already has assigned_to and reported_by
    
# app/core/ownership.py
class OwnershipService:
    @staticmethod
    async def can_access_resource(user_id: int, resource_type: str, resource_id: int, action: str, db: AsyncSession) -> bool:
        """Check if user can access specific resource instance"""
        # Check ownership, assignment, or creation
        # Consider hierarchical access (admin can access all)
```

#### Task 3.3: Context-Aware Permissions
**Points: 1** | **Priority: Medium**

```python
# app/core/context_permissions.py
class ContextPermission:
    @staticmethod
    async def can_modify_user(current_user: User, target_user: User, db: AsyncSession) -> bool:
        """Users can modify themselves, admins can modify lower-level users"""
        
    @staticmethod
    async def can_view_incident(current_user: User, incident: Incident, db: AsyncSession) -> bool:
        """Check if user can view specific incident based on assignment/reporting"""
```

### Phase 4: API Integration (2-3 story points)

#### Task 4.1: Update Authentication Endpoints  
**Points: 1** | **Priority: High**

```python
# app/api/auth.py - Update to include permissions in token/response
@router.post("/login", response_model=TokenWithPermissions)
async def login(user_credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    # ... existing login logic ...
    
    # Get user permissions
    permissions = await PermissionService.get_user_permissions(user.id, db)
    
    return TokenWithPermissions(
        access_token=access_token,
        refresh_token=refresh_token, 
        token_type="bearer",
        permissions=list(permissions),
        role=user.role.name
    )
```

#### Task 4.2: Refactor Existing API Endpoints
**Points: 2** | **Priority: High**

Replace hardcoded role checks with permission-based decorators:

```python
# app/api/cameras.py - Before
@router.post("/", response_model=CameraResponse)
async def create_camera(
    camera_data: CameraCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator_or_admin)  # OLD
):

# After  
@router.post("/", response_model=CameraResponse)
async def create_camera(
    camera_data: CameraCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("cameras:write"))  # NEW
):
```

### Phase 5: Management APIs (1-2 story points)

#### Task 5.1: Role Management API
**Points: 1** | **Priority: Medium**

```python
# app/api/roles.py
@router.get("/", response_model=List[RoleResponse])
async def get_roles(current_user: User = Depends(require_permission("roles:read"))):

@router.post("/", response_model=RoleResponse)  
async def create_role(current_user: User = Depends(require_permission("roles:write"))):

@router.put("/{role_id}/permissions")
async def update_role_permissions(current_user: User = Depends(require_permission("roles:write"))):
```

#### Task 5.2: User Permission Management API
**Points: 1** | **Priority: Medium**

```python
# app/api/user_permissions.py
@router.post("/users/{user_id}/permissions")
async def grant_user_permission(current_user: User = Depends(require_permission("users:grant_permissions"))):

@router.delete("/users/{user_id}/permissions/{permission_id}")
async def revoke_user_permission(current_user: User = Depends(require_permission("users:revoke_permissions"))):
```

---

## Best Practices & Design Principles

### 1. **Principle of Least Privilege**
- Users get minimum permissions needed for their role
- Explicit permission grants rather than broad access
- Regular permission auditing capabilities

### 2. **Hierarchical Inheritance**
```python
# Parent roles inherit permissions to children
ROLE_HIERARCHY = {
    "super_admin": [],  # All permissions
    "admin": ["super_admin"],
    "operator": ["admin"], 
    "viewer": ["operator"]
}
```

### 3. **Resource-Based Permissions**
```python
# Granular control over resources
"cameras:read"     # Can view cameras
"cameras:write"    # Can create/update cameras  
"cameras:delete"   # Can delete cameras
"incidents:assign" # Can assign incidents
```

### 4. **Caching Strategy**
```python
# app/core/permissions.py
from functools import lru_cache
import redis

class PermissionCache:
    @staticmethod
    async def get_cached_permissions(user_id: int) -> Set[str]:
        # Use Redis to cache user permissions for 15 minutes
        # Cache key: f"user_permissions:{user_id}"
```

### 5. **Audit Logging**
```python
# app/models/audit_log.py
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100))  # "permission_granted", "role_changed"
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
```

---

## Migration Strategy

### 1. **Backward Compatibility** (Critical)
- Keep existing role field during transition
- Dual-mode operation: support both old and new permission systems
- Gradual endpoint migration

### 2. **Data Migration Steps**
```sql
-- 1. Create new tables
-- 2. Migrate existing users to new role system
INSERT INTO roles (name, display_name, level) VALUES 
  ('admin', 'Administrator', 1),
  ('operator', 'Operator', 2), 
  ('viewer', 'Viewer', 3);

-- 3. Update user records
UPDATE users SET role_id = (SELECT id FROM roles WHERE name = users.role);

-- 4. Drop old role column (after full migration)
```

### 3. **Testing Strategy**
- Unit tests for permission service
- Integration tests for API endpoints
- Performance tests for permission checking
- Security audit for privilege escalation

---

## Estimated Timeline

- **Phase 1 (Foundation)**: 1-2 weeks
- **Phase 2 (Permission System)**: 1 week  
- **Phase 3 (UBAC)**: 3-5 days
- **Phase 4 (API Integration)**: 1 week
- **Phase 5 (Management)**: 2-3 days

**Total: 3-4 weeks** for complete implementation

---

## Risk Mitigation

### High Risk Items
1. **Breaking existing functionality** - Comprehensive testing required
2. **Performance impact** - Implement caching early
3. **Complex permission inheritance** - Start simple, iterate

### Medium Risk Items  
1. **Database migration complexity** - Test on staging first
2. **Frontend compatibility** - Coordinate token format changes

---

## Success Criteria

### ✅ Definition of Done
- [x] ~~Hierarchical role system working~~
- [x] ~~User-specific permissions functional~~
- [x] ~~All existing endpoints migrated~~
- [x] ~~Permission caching implemented~~
- [x] ~~Audit logging active~~
- [x] ~~Management APIs complete~~
- [ ] Documentation updated
- [ ] Test coverage >80%
- [ ] Performance benchmarks met
- [ ] Security audit passed

This implementation will transform the current basic role system into a flexible, maintainable, and scalable RBAC+UBAC solution that can grow with the application's needs.

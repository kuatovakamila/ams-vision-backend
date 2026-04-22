# Camera Modules System - Review Route

## Review Flow: Where to Start → Where to Go → Where to Finish

### 🚀 **START HERE: Entry Point**

#### 1. `app/main.py`
- **What to check**: New routers imported and registered
- **Look for**: 
  - Import of `camera_modules` and `tenant_modules`
  - Router registration with prefixes `/api/v1/camera-modules` and `/api/v1/tenants`
- **Lines**: ~22-24 (imports), ~164-174 (router registration)

---

### 📊 **Step 2: Database Layer (Bottom-Up)**

#### 2.1 `app/models/camera_feature.py`
- **What to check**: Feature model structure
- **Look for**: 
  - `code` as TEXT primary key
  - Relationships to modules and tenant_overrides
- **Key fields**: `code`, `name`, `description`

#### 2.2 `app/models/camera_module.py`
- **What to check**: Module model and association table
- **Look for**: 
  - `camera_module_features` association table
  - Module model with `code` as TEXT primary key
  - Relationships to features and tenant_assignments

#### 2.3 `app/models/tenant_camera_module.py`
- **What to check**: Tenant-module assignment model
- **Look for**: 
  - Composite primary key (tenant_id, module_code)
  - `enabled` boolean field
  - Foreign keys to tenants and camera_modules

#### 2.4 `app/models/tenant_feature_override.py`
- **What to check**: Feature override model
- **Look for**: 
  - Composite primary key (tenant_id, feature_code)
  - `enabled` boolean (force enable/disable)
  - Foreign keys to tenants and features

#### 2.5 `app/models/tenant.py`
- **What to check**: Updated relationships
- **Look for**: 
  - `camera_modules` relationship
  - `feature_overrides` relationship
- **Lines**: ~40-45

#### 2.6 `app/models/__init__.py`
- **What to check**: All new models exported
- **Look for**: 
  - Imports of CameraFeature, CameraModule, TenantCameraModule, TenantFeatureOverride
  - Exports in `__all__` list

---

### 🗄️ **Step 3: Database Migration**

#### 3. `alembic/versions/a1b2c3d4e5f6_add_camera_modules_system.py`
- **What to check**: Migration script
- **Look for**: 
  - All 5 tables created (features, camera_modules, camera_module_features, tenant_camera_modules, tenant_features_override)
  - Foreign key constraints
  - Initial seed data (7 features, 3 modules, feature assignments)
- **Key sections**: 
  - `upgrade()` function creates tables
  - Seed data inserts features and modules
  - `downgrade()` function drops tables

---

### 📝 **Step 4: Data Schemas (API Contracts)**

#### 4.1 `app/schemas/camera_feature.py`
- **What to check**: Feature request/response schemas
- **Look for**: 
  - `CameraFeatureCreate`, `CameraFeatureUpdate`, `CameraFeatureResponse`
  - Field validations

#### 4.2 `app/schemas/camera_module.py`
- **What to check**: Module schemas with feature relationships
- **Look for**: 
  - `CameraModuleCreate` with `feature_codes` list
  - `CameraModuleDetailResponse` with features list
  - Feature assignment schemas

#### 4.3 `app/schemas/tenant_module.py`
- **What to check**: Tenant assignment schemas
- **Look for**: 
  - `TenantModuleAssignment`, `TenantModuleResponse`
  - `TenantFeatureOverrideCreate`, `TenantFeatureOverrideResponse`
  - `TenantFeaturesResponse` (computed features)

---

### 🔧 **Step 5: Business Logic (CRUD)**

#### 5.1 `app/crud/camera_feature.py`
- **What to check**: Feature CRUD operations
- **Look for**: 
  - `get()`, `get_multi()`, `create()`, `update()`, `delete()`
  - `count_modules_with_feature()` helper
- **Key class**: `CameraFeatureCRUD`

#### 5.2 `app/crud/camera_module.py`
- **What to check**: Module CRUD with feature management
- **Look for**: 
  - `create()` with feature assignment
  - `add_feature()`, `remove_feature()` methods
  - `count_tenants_with_module()` helper
- **Key class**: `CameraModuleCRUD`

#### 5.3 `app/crud/tenant_module.py`
- **What to check**: Tenant assignment and override operations
- **Look for**: 
  - `assign_module()`, `remove_module()`
  - `create_feature_override()`, `remove_feature_override()`
  - `get_tenant_modules()`, `get_tenant_feature_overrides()`
- **Key class**: `TenantModuleCRUD`

#### 5.4 `app/crud/__init__.py`
- **What to check**: CRUD instances exported
- **Look for**: 
  - Exports of `camera_feature_crud`, `camera_module_crud`, `tenant_module_crud`

---

### ⚙️ **Step 6: Service Layer (Feature Checking Logic)**

#### 6. `app/services/camera_feature_service.py`
- **What to check**: Core feature checking logic
- **Look for**: 
  - `has_feature(tenant_id, feature_code)` - Main check function
  - `get_tenant_features(tenant_id)` - Get all enabled features
  - `get_tenant_feature_codes(tenant_id)` - Get feature codes set
  - Redis caching implementation
  - **Override precedence logic**: Overrides checked first, then module features
- **Key class**: `CameraFeatureService`
- **Critical logic**: Lines ~60-100 (has_feature method)

---

### 🌐 **Step 7: API Endpoints (REST API)**

#### 7.1 `app/api/camera_modules.py`
- **What to check**: Module management endpoints
- **Endpoints to review**:
  - `GET /camera-modules` - List modules
  - `POST /camera-modules` - Create module
  - `GET /camera-modules/{code}` - Get module details
  - `PUT /camera-modules/{code}` - Update module
  - `DELETE /camera-modules/{code}` - Delete module
  - `GET /camera-modules/{code}/features` - List module features
  - `POST /camera-modules/{code}/features` - Add feature to module
  - `DELETE /camera-modules/{code}/features/{feature_code}` - Remove feature
- **Look for**: 
  - Superadmin permission checks
  - Validation logic
  - Error handling

#### 7.2 `app/api/tenant_modules.py`
- **What to check**: Tenant module assignment endpoints
- **Endpoints to review**:
  - `GET /tenants/{tenant_id}/modules` - Get tenant's modules
  - `POST /tenants/{tenant_id}/modules` - Assign module to tenant
  - `DELETE /tenants/{tenant_id}/modules/{module_code}` - Remove module
  - `GET /tenants/{tenant_id}/features` - Get computed features
  - `POST /tenants/{tenant_id}/features/override` - Create override
  - `DELETE /tenants/{tenant_id}/features/override/{feature_code}` - Remove override
- **Look for**: 
  - Permission checks (superadmin or tenant user)
  - Cache invalidation calls
  - Feature service integration

---

### ✅ **FINISH HERE: Integration Points**

#### 8. **Verify Integration**
- **Check `app/main.py`** again:
  - Routers properly registered
  - No import errors
  
#### 9. **Test the Flow**
Suggested test sequence:
1. **Create a feature** → `POST /api/v1/camera-modules` (but first create features via direct DB or add feature endpoints)
2. **Create a module** → `POST /api/v1/camera-modules` with feature_codes
3. **Assign module to tenant** → `POST /api/v1/tenants/{id}/modules`
4. **Check tenant features** → `GET /api/v1/tenants/{id}/features`
5. **Add feature override** → `POST /api/v1/tenants/{id}/features/override`
6. **Verify override precedence** → `GET /api/v1/tenants/{id}/features` again

---

## 🗺️ **Quick Navigation Map**

```
START: app/main.py
  ↓
DATABASE LAYER:
  app/models/camera_feature.py
  app/models/camera_module.py
  app/models/tenant_camera_module.py
  app/models/tenant_feature_override.py
  app/models/tenant.py (updated)
  app/models/__init__.py
  ↓
MIGRATION:
  alembic/versions/a1b2c3d4e5f6_add_camera_modules_system.py
  ↓
SCHEMAS:
  app/schemas/camera_feature.py
  app/schemas/camera_module.py
  app/schemas/tenant_module.py
  ↓
CRUD:
  app/crud/camera_feature.py
  app/crud/camera_module.py
  app/crud/tenant_module.py
  app/crud/__init__.py
  ↓
SERVICE:
  app/services/camera_feature_service.py ⭐ (Core Logic)
  ↓
API:
  app/api/camera_modules.py
  app/api/tenant_modules.py
  ↓
FINISH: app/main.py (verify integration)
```

---

## 🎯 **Key Review Points**

1. **Feature Override Logic**: Check `camera_feature_service.py` → `has_feature()` method
2. **Module-Feature Relationship**: Check `camera_module.py` → association table
3. **Tenant Assignment**: Check `tenant_modules.py` → assignment endpoints
4. **Cache Invalidation**: Check `tenant_modules.py` → cache invalidation calls
5. **Permission Checks**: Check both API files → superadmin checks

---

## 📋 **Review Checklist**

- [ ] All models have proper relationships
- [ ] Migration creates all tables correctly
- [ ] Seed data is complete (7 features, 3 modules)
- [ ] CRUD operations handle all cases
- [ ] Feature service override logic is correct
- [ ] API endpoints have proper permissions
- [ ] Cache invalidation works
- [ ] Error handling is comprehensive
- [ ] All imports are correct
- [ ] No circular dependencies

---

**Total Files to Review: 15 files**
**Estimated Review Time: 30-45 minutes**


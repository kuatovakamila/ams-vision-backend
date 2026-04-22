# Import all models here for Alembic to detect them
from ..core.database import Base
from .user import User
from .camera import Camera
from .incident import Incident
from .event import Event
from .file import File
from .folder import Folder
from .permission import Permission
from .role import Role
from .user_permission import UserPermission, user_permissions
from .audit_log import AuditLog
from .camera_feature import CameraFeature
from .camera_module import CameraModule, camera_module_features
from .tenant_camera_module import TenantCameraModule
from .tenant_feature_override import TenantFeatureOverride

__all__ = [
    "Base",
    "User",
    "Camera",
    "Incident",
    "Event",
    "File",
    "Folder",
    "Permission",
    "Role",
    "UserPermission",
    "user_permissions",
    "AuditLog",
    "CameraFeature",
    "CameraModule",
    "camera_module_features",
    "TenantCameraModule",
    "TenantFeatureOverride",
]

from .camera_feature import camera_feature_repository
from .camera_module import camera_module_repository
from .tenant_module import tenant_module_repository
from .role import role_repository
from .permission import permission_repository, user_permission_repository

__all__ = [
    "camera_feature_repository",
    "camera_module_repository",
    "tenant_module_repository",
    "role_repository",
    "permission_repository",
    "user_permission_repository",
]


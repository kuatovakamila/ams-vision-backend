from typing import List, Dict, Any, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://ams_user:ams_password@localhost:5432/ams_db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Application
    environment: str = "development"
    debug: bool = True
    cors_origins: List[str] = [
        "*",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    # File Upload
    upload_dir: str = "uploads"
    max_file_size: int = 4294967296  # 4GB
    allow_all_extensions: bool = False  # Set to True to allow any file type
    allowed_extensions: List[str] = [
        # Images
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "tiff",
        "tif",
        "webp",
        "heic",
        "heif",
        "svg",
        # Documents
        "pdf",
        "doc",
        "docx",
        "txt",
        "rtf",
        "odt",
        "pages",
        # Spreadsheets
        "csv",
        "xlsx",
        "xls",
        "ods",
        "numbers",
        # Presentations
        "ppt",
        "pptx",
        "odp",
        "key",
        # Archives
        "zip",
        "rar",
        "7z",
        "tar",
        "gz",
        "bz2",
        # Video
        "mp4",
        "avi",
        "mov",
        "wmv",
        "flv",
        "webm",
        "mkv",
        "m4v",
        # Audio
        "mp3",
        "wav",
        "aac",
        "flac",
        "ogg",
        "wma",
        "m4a",
        # Data formats
        "json",
        "xml",
        "yaml",
        "yml",
        "sql",
        # Other common formats
        "eps",
        "ai",
        "psd",
        "sketch",
        "fig",
    ]

    # MinIO Configuration
    minio_endpoint: str = "minio.trackfacility.com"
    minio_access_key: str = "w0lZdDZdKEfYcKiiyxJB"
    minio_secret_key: str = "mkptG8MT00PVK8YW7Cjtu49XTA6pcvYEAviL4KVx"
    minio_bucket: str = "clients-bucket"
    minio_folder_prefix: str = "esg-group-folder"  # Folder within bucket
    minio_secure: bool = True  # Use HTTPS
    minio_region: str = "us-east-1"
    minio_presigned_url_expiry: int = 3600  # 1 hour in seconds

    # Frigate Configuration
    frigate_base_url: Optional[str] = None  # Base URL for Frigate (e.g., http://frigate:5000)

    # Logging
    log_level: str = "INFO"

    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "AMS Backend"
    version: str = "0.0.8"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache()
def get_settings():
    """Get application settings with caching"""
    return Settings()


# Default settings instance
settings = get_settings()


class TenantSettings:
    """
    Tenant-specific settings that override global settings.
    This class merges tenant-specific settings from the database with global settings.
    """

    def __init__(
        self,
        tenant_id: Optional[int] = None,
        tenant_settings: Optional[Dict[str, Any]] = None,
    ):
        self.tenant_id = tenant_id
        self.tenant_settings = tenant_settings or {}
        self.global_settings = get_settings()

    def __getattr__(self, name: str):
        """
        Get a setting value, prioritizing tenant-specific settings over global settings.
        """
        # Check if the setting exists in tenant settings
        if name in self.tenant_settings:
            return self.tenant_settings[name]

        # Fall back to global settings
        if hasattr(self.global_settings, name):
            return getattr(self.global_settings, name)

        # Setting not found
        raise AttributeError(f"'TenantSettings' object has no attribute '{name}'")

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a setting value with a default fallback.
        """
        try:
            return self.__getattr__(name)
        except AttributeError:
            return default


def get_tenant_settings(
    tenant_id: Optional[int] = None, tenant_settings: Optional[Dict[str, Any]] = None
) -> TenantSettings:
    """
    Get tenant-specific settings.
    If tenant_id is None or tenant_settings is None, returns global settings.
    """
    if tenant_id is None or tenant_settings is None:
        return TenantSettings()

    return TenantSettings(tenant_id=tenant_id, tenant_settings=tenant_settings)

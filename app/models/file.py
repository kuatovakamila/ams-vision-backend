from sqlalchemy import Column, Integer, String, DateTime, BigInteger, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
from .base import TenantMixin


class File(Base, TenantMixin):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)

    # Set the tenant relationship
    tenant = relationship("Tenant", back_populates="files")
    filename = Column(
        String(255), nullable=False
    )  # Unique filename in storage (UUID-based)
    original_filename = Column(
        String(255), nullable=False
    )  # Original filename from upload
    file_path = Column(String(500), nullable=False)  # MinIO object name/path
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=True)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    uploader = relationship("User", backref="uploaded_files")
    incident = relationship("Incident", backref="files")
    folder = relationship("Folder", back_populates="files")

    def __repr__(self):
        return (
            f"<File(id={self.id}, filename='{self.filename}', size={self.file_size})>"
        )

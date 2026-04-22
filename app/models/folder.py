from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
from .base import TenantMixin


class Folder(Base, TenantMixin):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)

    # Set the tenant relationship
    tenant = relationship("Tenant", back_populates="folders")
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True, index=True)
    path = Column(String(1000), nullable=False, index=True)  # Computed full path
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    parent = relationship("Folder", remote_side=[id], backref="children")
    creator = relationship("User", backref="created_folders")
    files = relationship("File", back_populates="folder")

    def __repr__(self):
        return f"<Folder(id={self.id}, name='{self.name}', path='{self.path}')>"

    def get_full_path(self) -> str:
        """Get the full path of the folder"""
        return self.path

    def is_root_folder(self) -> bool:
        """Check if this is a root folder (no parent)"""
        return self.parent_id is None

    def get_ancestors(self):
        """Get all ancestor folders"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_descendants(self):
        """Get all descendant folders (recursive)"""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def calculate_path(self) -> str:
        """Calculate the full path based on parent hierarchy"""
        if self.parent_id is None:
            return f"/{self.name}"

        # Get parent path and append current folder name
        parent_path = self.parent.path if self.parent else ""
        return f"{parent_path}/{self.name}"

    def update_path(self):
        """Update the path field based on current hierarchy"""
        self.path = self.calculate_path()

    def update_descendants_paths(self):
        """Update paths for all descendant folders"""
        for child in self.children:
            child.update_path()
            child.update_descendants_paths()

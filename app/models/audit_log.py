from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Who performed the action
    target_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # Who was affected
    action = Column(
        String(100), nullable=False, index=True
    )  # "permission_granted", "role_changed", etc.
    resource_type = Column(
        String(50), nullable=True, index=True
    )  # "user", "role", "permission"
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)  # Additional context
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="audit_actions")
    target_user = relationship(
        "User", foreign_keys=[target_user_id], backref="audit_targets"
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action='{self.action}', resource_type='{self.resource_type}')>"

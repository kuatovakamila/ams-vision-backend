from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship


class TenantMixin:
    """
    Mixin class to add tenant relationship to models.
    This mixin should be applied to all models that need tenant isolation.
    """

    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The back_populates attribute will be set by each model class
    # This is just a placeholder that will be overridden
    tenant = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

"""merge tenant table with existing migrations

Revision ID: bf8e0b644e50
Revises: 49b336de21b4, add_tenant_table
Create Date: 2025-08-28 18:15:24.232375

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bf8e0b644e50'
down_revision = ('49b336de21b4', 'add_tenant_table')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

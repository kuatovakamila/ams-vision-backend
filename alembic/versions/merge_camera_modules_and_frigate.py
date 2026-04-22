"""merge camera modules and frigate fields

Revision ID: merge_camera_modules_and_frigate
Revises: a1b2c3d4e5f6, f8a9b2c3d4e5
Create Date: 2026-04-21

"""
from alembic import op
import sqlalchemy as sa

revision = 'merge_camera_modules_and_frigate'
down_revision = ('a1b2c3d4e5f6', 'f8a9b2c3d4e5')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass

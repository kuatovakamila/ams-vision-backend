"""add frigate fields to events

Revision ID: f8a9b2c3d4e5
Revises: 72ab99a16c31
Create Date: 2025-11-07 21:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'f8a9b2c3d4e5'
down_revision = '72ab99a16c31'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Frigate-specific columns to events table
    op.add_column('events', sa.Column('frigate_event_id', sa.String(length=100), nullable=True))
    op.add_column('events', sa.Column('frigate_type', sa.String(length=20), nullable=True))
    op.add_column('events', sa.Column('object_type', sa.String(length=50), nullable=True))
    op.add_column('events', sa.Column('confidence', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('snapshot_url', sa.String(length=500), nullable=True))
    op.add_column('events', sa.Column('clip_url', sa.String(length=500), nullable=True))
    op.add_column('events', sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('events', sa.Column('frigate_timestamp', sa.DateTime(timezone=True), nullable=True))
    
    # Create indexes for better query performance
    op.create_index(op.f('ix_events_frigate_event_id'), 'events', ['frigate_event_id'], unique=True)
    op.create_index(op.f('ix_events_frigate_type'), 'events', ['frigate_type'], unique=False)
    op.create_index(op.f('ix_events_object_type'), 'events', ['object_type'], unique=False)
    op.create_index(op.f('ix_events_camera_id'), 'events', ['camera_id'], unique=False)
    op.create_index(op.f('ix_events_created_at'), 'events', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_events_created_at'), table_name='events')
    op.drop_index(op.f('ix_events_camera_id'), table_name='events')
    op.drop_index(op.f('ix_events_object_type'), table_name='events')
    op.drop_index(op.f('ix_events_frigate_type'), table_name='events')
    op.drop_index(op.f('ix_events_frigate_event_id'), table_name='events')
    
    # Drop columns
    op.drop_column('events', 'frigate_timestamp')
    op.drop_column('events', 'metadata')
    op.drop_column('events', 'clip_url')
    op.drop_column('events', 'snapshot_url')
    op.drop_column('events', 'confidence')
    op.drop_column('events', 'object_type')
    op.drop_column('events', 'frigate_type')
    op.drop_column('events', 'frigate_event_id')


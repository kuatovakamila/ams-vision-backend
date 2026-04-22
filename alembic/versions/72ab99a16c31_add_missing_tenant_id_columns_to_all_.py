"""add missing tenant_id columns to all tables

Revision ID: 72ab99a16c31
Revises: 597992c21890
Create Date: 2025-08-28 18:43:12.047382

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '72ab99a16c31'
down_revision = '597992c21890'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure default tenant exists
    op.execute(
        """
        INSERT INTO tenants (name, slug, status)
        VALUES ('Default Tenant', 'default', 'active')
        ON CONFLICT (slug) DO NOTHING
        """
    )
    
    # Add tenant_id to cameras table
    op.add_column('cameras', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_cameras_tenant_id'), 'cameras', ['tenant_id'], unique=False)
    op.create_foreign_key('fk_cameras_tenant_id', 'cameras', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.execute(
        """
        UPDATE cameras
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )
    op.alter_column('cameras', 'tenant_id', nullable=False)
    
    # Add tenant_id to incidents table
    op.add_column('incidents', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_incidents_tenant_id'), 'incidents', ['tenant_id'], unique=False)
    op.create_foreign_key('fk_incidents_tenant_id', 'incidents', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.execute(
        """
        UPDATE incidents
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )
    op.alter_column('incidents', 'tenant_id', nullable=False)
    
    # Add tenant_id to events table
    op.add_column('events', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_events_tenant_id'), 'events', ['tenant_id'], unique=False)
    op.create_foreign_key('fk_events_tenant_id', 'events', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.execute(
        """
        UPDATE events
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )
    op.alter_column('events', 'tenant_id', nullable=False)
    
    # Add tenant_id to files table
    op.add_column('files', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_files_tenant_id'), 'files', ['tenant_id'], unique=False)
    op.create_foreign_key('fk_files_tenant_id', 'files', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.execute(
        """
        UPDATE files
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )
    op.alter_column('files', 'tenant_id', nullable=False)
    
    # Add tenant_id to folders table
    op.add_column('folders', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_folders_tenant_id'), 'folders', ['tenant_id'], unique=False)
    op.create_foreign_key('fk_folders_tenant_id', 'folders', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.execute(
        """
        UPDATE folders
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )
    op.alter_column('folders', 'tenant_id', nullable=False)
    
    # Add tenant_id to roles table
    op.add_column('roles', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_roles_tenant_id'), 'roles', ['tenant_id'], unique=False)
    op.create_foreign_key('fk_roles_tenant_id', 'roles', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.execute(
        """
        UPDATE roles
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )
    op.alter_column('roles', 'tenant_id', nullable=False)


def downgrade() -> None:
    # Remove tenant_id from all tables
    tables = ['cameras', 'incidents', 'events', 'files', 'folders', 'roles']
    
    for table in tables:
        op.drop_constraint(f'fk_{table}_tenant_id', table, type_='foreignkey')
        op.drop_index(op.f(f'ix_{table}_tenant_id'), table_name=table)
        op.drop_column(table, 'tenant_id')

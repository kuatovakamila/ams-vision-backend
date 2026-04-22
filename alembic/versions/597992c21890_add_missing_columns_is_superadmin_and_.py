"""add missing columns is_superadmin and tenant_id to users

Revision ID: 597992c21890
Revises: d53ca74fdce7
Create Date: 2025-08-28 18:32:17.112056

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '597992c21890'
down_revision = 'bf8e0b644e50'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_superadmin column to users table
    op.add_column('users', sa.Column('is_superadmin', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add tenant_id to users table
    op.add_column('users', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_users_tenant_id'), 'users', ['tenant_id'], unique=False)
    op.create_foreign_key('fk_users_tenant_id', 'users', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    
    # Set default tenant_id for existing users (ensure default tenant exists)
    op.execute(
        """
        INSERT INTO tenants (name, slug, status)
        VALUES ('Default Tenant', 'default', 'active')
        ON CONFLICT (slug) DO NOTHING
        """
    )
    
    op.execute(
        """
        UPDATE users
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )
    
    # Make tenant_id not nullable
    op.alter_column('users', 'tenant_id', nullable=False)


def downgrade() -> None:
    # Remove tenant_id from users table
    op.drop_constraint('fk_users_tenant_id', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_tenant_id'), table_name='users')
    op.drop_column('users', 'tenant_id')
    
    # Remove is_superadmin column from users table
    op.drop_column('users', 'is_superadmin')

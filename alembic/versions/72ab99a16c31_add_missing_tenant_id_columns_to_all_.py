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


def _has_column(conn, table, column):
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None


def _has_index(conn, index_name):
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname=:i"
    ), {"i": index_name})
    return result.fetchone() is not None


def _has_fk(conn, table, fk_name):
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conrelid=(SELECT oid FROM pg_class WHERE relname=:t) AND conname=:n AND contype='f'"
    ), {"t": table, "n": fk_name})
    return result.fetchone() is not None


def _add_tenant_id(conn, table):
    if not _has_column(conn, table, 'tenant_id'):
        op.add_column(table, sa.Column('tenant_id', sa.Integer(), nullable=True))

    if not _has_index(conn, f'ix_{table}_tenant_id'):
        op.create_index(op.f(f'ix_{table}_tenant_id'), table, ['tenant_id'], unique=False)

    if not _has_fk(conn, table, f'fk_{table}_tenant_id'):
        op.create_foreign_key(f'fk_{table}_tenant_id', table, 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    op.execute(sa.text(
        f"UPDATE {table} SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default') WHERE tenant_id IS NULL"
    ))
    op.alter_column(table, 'tenant_id', nullable=False)


def upgrade() -> None:
    conn = op.get_bind()

    op.execute(sa.text(
        """
        INSERT INTO tenants (name, slug, status)
        VALUES ('Default Tenant', 'default', 'active')
        ON CONFLICT (slug) DO NOTHING
        """
    ))

    for table in ['cameras', 'incidents', 'events', 'files', 'folders', 'roles']:
        _add_tenant_id(conn, table)


def downgrade() -> None:
    # Remove tenant_id from all tables
    tables = ['cameras', 'incidents', 'events', 'files', 'folders', 'roles']
    
    for table in tables:
        op.drop_constraint(f'fk_{table}_tenant_id', table, type_='foreignkey')
        op.drop_index(op.f(f'ix_{table}_tenant_id'), table_name=table)
        op.drop_column(table, 'tenant_id')

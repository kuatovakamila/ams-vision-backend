"""Add tenant table and tenant_id to existing tables

Revision ID: add_tenant_table
Revises: e7d0b31d2cd3
Create Date: 2025-08-19 10:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = "add_tenant_table"
down_revision = "e7d0b31d2cd3"
branch_labels = None
depends_on = None


def upgrade():
    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default=sa.text("'active'"),
            nullable=True,
        ),
        sa.Column("subscription_plan", sa.String(length=50), nullable=True),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("settings", JSON, server_default=sa.text("'{}'"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_id"), "tenants", ["id"], unique=False)
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)

    # Create default tenant
    op.execute(
        """
        INSERT INTO tenants (name, slug, status)
        VALUES ('Default Tenant', 'default', 'active')
        """
    )

    # Add tenant_id to users table
    op.add_column("users", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_users_tenant_id",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Set default tenant_id for existing users
    op.execute(
        """
        UPDATE users
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )

    # Make tenant_id not nullable
    op.alter_column("users", "tenant_id", nullable=False)

    # Add tenant_id to cameras table
    op.add_column("cameras", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_cameras_tenant_id"), "cameras", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        "fk_cameras_tenant_id",
        "cameras",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Set default tenant_id for existing cameras
    op.execute(
        """
        UPDATE cameras
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )

    # Make tenant_id not nullable
    op.alter_column("cameras", "tenant_id", nullable=False)

    # Add tenant_id to incidents table
    op.add_column("incidents", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_incidents_tenant_id"), "incidents", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        "fk_incidents_tenant_id",
        "incidents",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Set default tenant_id for existing incidents
    op.execute(
        """
        UPDATE incidents
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )

    # Make tenant_id not nullable
    op.alter_column("incidents", "tenant_id", nullable=False)

    # Add tenant_id to events table
    op.add_column("events", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_events_tenant_id"), "events", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_events_tenant_id",
        "events",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Set default tenant_id for existing events
    op.execute(
        """
        UPDATE events
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )

    # Make tenant_id not nullable
    op.alter_column("events", "tenant_id", nullable=False)

    # Add tenant_id to files table
    op.add_column("files", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_files_tenant_id"), "files", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_files_tenant_id",
        "files",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Set default tenant_id for existing files
    op.execute(
        """
        UPDATE files
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )

    # Make tenant_id not nullable
    op.alter_column("files", "tenant_id", nullable=False)

    # Add tenant_id to folders table
    op.add_column("folders", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_folders_tenant_id"), "folders", ["tenant_id"], unique=False
    )
    op.create_foreign_key(
        "fk_folders_tenant_id",
        "folders",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Set default tenant_id for existing folders
    op.execute(
        """
        UPDATE folders
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )

    # Make tenant_id not nullable
    op.alter_column("folders", "tenant_id", nullable=False)

    # Add tenant_id to roles table
    op.add_column("roles", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_roles_tenant_id"), "roles", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_roles_tenant_id",
        "roles",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Set default tenant_id for existing roles
    op.execute(
        """
        UPDATE roles
        SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
        WHERE tenant_id IS NULL
        """
    )

    # Make tenant_id not nullable
    op.alter_column("roles", "tenant_id", nullable=False)


def downgrade():
    # Drop foreign keys
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_constraint("fk_cameras_tenant_id", "cameras", type_="foreignkey")
    op.drop_constraint("fk_incidents_tenant_id", "incidents", type_="foreignkey")
    op.drop_constraint("fk_events_tenant_id", "events", type_="foreignkey")
    op.drop_constraint("fk_files_tenant_id", "files", type_="foreignkey")
    op.drop_constraint("fk_folders_tenant_id", "folders", type_="foreignkey")
    op.drop_constraint("fk_roles_tenant_id", "roles", type_="foreignkey")

    # Drop indexes
    op.drop_index(op.f("ix_users_tenant_id"), table_name="users")
    op.drop_index(op.f("ix_cameras_tenant_id"), table_name="cameras")
    op.drop_index(op.f("ix_incidents_tenant_id"), table_name="incidents")
    op.drop_index(op.f("ix_events_tenant_id"), table_name="events")
    op.drop_index(op.f("ix_files_tenant_id"), table_name="files")
    op.drop_index(op.f("ix_folders_tenant_id"), table_name="folders")
    op.drop_index(op.f("ix_roles_tenant_id"), table_name="roles")

    # Drop columns
    op.drop_column("users", "tenant_id")
    op.drop_column("cameras", "tenant_id")
    op.drop_column("incidents", "tenant_id")
    op.drop_column("events", "tenant_id")
    op.drop_column("files", "tenant_id")
    op.drop_column("folders", "tenant_id")
    op.drop_column("roles", "tenant_id")

    # Drop tenants table
    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_id"), table_name="tenants")
    op.drop_table("tenants")

"""add camera modules system

Revision ID: a1b2c3d4e5f6
Revises: 72ab99a16c31
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '72ab99a16c31'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create features table
    op.create_table(
        'features',
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('code')
    )
    op.create_index(op.f('ix_features_code'), 'features', ['code'], unique=False)

    # Create camera_modules table
    op.create_table(
        'camera_modules',
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('code')
    )
    op.create_index(op.f('ix_camera_modules_code'), 'camera_modules', ['code'], unique=False)

    # Create camera_module_features association table
    op.create_table(
        'camera_module_features',
        sa.Column('module_code', sa.String(length=100), nullable=False),
        sa.Column('feature_code', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['feature_code'], ['features.code'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['module_code'], ['camera_modules.code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('module_code', 'feature_code')
    )

    # Create tenant_camera_modules table
    op.create_table(
        'tenant_camera_modules',
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('module_code', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['module_code'], ['camera_modules.code'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tenant_id', 'module_code')
    )
    op.create_index(op.f('ix_tenant_camera_modules_tenant_id'), 'tenant_camera_modules', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_tenant_camera_modules_module_code'), 'tenant_camera_modules', ['module_code'], unique=False)

    # Create tenant_features_override table
    op.create_table(
        'tenant_features_override',
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('feature_code', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['feature_code'], ['features.code'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tenant_id', 'feature_code')
    )
    op.create_index(op.f('ix_tenant_features_override_tenant_id'), 'tenant_features_override', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_tenant_features_override_feature_code'), 'tenant_features_override', ['feature_code'], unique=False)

    # Seed initial features
    op.execute("""
        INSERT INTO features (code, name, description) VALUES
        ('people_count', 'People Count', 'Count the number of people in camera view'),
        ('heatmap', 'Heatmap', 'Generate heatmaps showing activity patterns'),
        ('fire_alert', 'Fire Alert', 'Detect fire and smoke in camera view'),
        ('helmet_detection', 'Helmet Detection', 'Detect if workers are wearing safety helmets'),
        ('zone_intrusion', 'Zone Intrusion', 'Detect unauthorized entry into restricted zones'),
        ('reception_activity', 'Reception Activity', 'Monitor activity at reception areas'),
        ('vehicle_detection', 'Vehicle Detection', 'Detect and classify vehicles')
        ON CONFLICT (code) DO NOTHING
    """)

    # Seed initial modules
    op.execute("""
        INSERT INTO camera_modules (code, name, description) VALUES
        ('hotel', 'Hotel Module', 'Module for hotel businesses with people counting, heatmaps, and reception monitoring'),
        ('cafe', 'Cafe Module', 'Module for cafes and restaurants with people counting and heatmaps'),
        ('oil_gas', 'Oil & Gas Module', 'Module for oil and gas facilities with safety features like helmet detection, fire alerts, zone intrusion, and vehicle detection')
        ON CONFLICT (code) DO NOTHING
    """)

    # Assign features to hotel module
    op.execute("""
        INSERT INTO camera_module_features (module_code, feature_code) VALUES
        ('hotel', 'people_count'),
        ('hotel', 'heatmap'),
        ('hotel', 'reception_activity')
        ON CONFLICT (module_code, feature_code) DO NOTHING
    """)

    # Assign features to cafe module
    op.execute("""
        INSERT INTO camera_module_features (module_code, feature_code) VALUES
        ('cafe', 'people_count'),
        ('cafe', 'heatmap')
        ON CONFLICT (module_code, feature_code) DO NOTHING
    """)

    # Assign features to oil_gas module
    op.execute("""
        INSERT INTO camera_module_features (module_code, feature_code) VALUES
        ('oil_gas', 'helmet_detection'),
        ('oil_gas', 'fire_alert'),
        ('oil_gas', 'zone_intrusion'),
        ('oil_gas', 'vehicle_detection')
        ON CONFLICT (module_code, feature_code) DO NOTHING
    """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('tenant_features_override')
    op.drop_table('tenant_camera_modules')
    op.drop_table('camera_module_features')
    op.drop_table('camera_modules')
    op.drop_table('features')


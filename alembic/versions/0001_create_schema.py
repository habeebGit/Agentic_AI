"""create initial schema

Revision ID: 0001_create_schema
Revises: 0000_create_extensions
Create Date: 2026-01-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_create_schema'
down_revision = '0000_create_extensions'
branch_labels = None
depends_on = None


def upgrade():
    # Extensions (pgcrypto, citext, pg_trgm, btree_gin) should be enabled by prior migration 0000_create_extensions.
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.Text(), nullable=False, unique=True),
        sa.Column('full_name', sa.Text(), nullable=True),
        sa.Column('role', sa.Text(), nullable=False, server_default='analyst'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('properties',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.Text()),
        sa.Column('property_type', sa.Text(), nullable=False),
        sa.Column('building_sqft', sa.Numeric()),
        sa.Column('lot_sqft', sa.Numeric()),
        sa.Column('year_built', sa.Integer()),
        sa.Column('stories', sa.Integer()),
        sa.Column('address_street', sa.Text(), nullable=False),
        sa.Column('address_city', sa.Text(), nullable=False),
        sa.Column('address_state', sa.Text(), nullable=False),
        sa.Column('address_zip', sa.Text(), nullable=False),
        sa.Column('address_country', sa.Text(), nullable=False, server_default='US'),
        sa.Column('lat', sa.Float()),
        sa.Column('lon', sa.Float()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_synced_at', sa.TIMESTAMP(timezone=True))
    )

    op.create_table('property_source_ids',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.Text(), nullable=False),
        sa.Column('provider_id', sa.Text(), nullable=False),
        sa.Column('raw_payload', sa.JSON()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('property_id', 'provider', 'provider_id')
    )

    op.create_table('provenance_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('field_path', sa.Text(), nullable=False),
        sa.Column('provider', sa.Text(), nullable=False),
        sa.Column('raw_reference', sa.Text()),
        sa.Column('fetched_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('confidence', sa.Numeric(), nullable=False),
        sa.Column('raw_value', sa.JSON()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('financials_last12mo',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('gross_income', sa.Numeric()),
        sa.Column('net_operating_income', sa.Numeric()),
        sa.Column('total_expenses', sa.Numeric()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('financials_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('noi', sa.Numeric()),
        sa.Column('gross', sa.Numeric()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('leases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tenant_name', sa.Text()),
        sa.Column('leased_sqft', sa.Numeric()),
        sa.Column('lease_start', sa.Date()),
        sa.Column('lease_end', sa.Date()),
        sa.Column('rent_psf', sa.Numeric()),
        sa.Column('source', sa.Text()),
        sa.Column('raw_payload', sa.JSON()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('url', sa.Text()),
        sa.Column('mime_type', sa.Text()),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('raw_metadata', sa.JSON()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('comps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.Text()),
        sa.Column('sale_date', sa.Date()),
        sa.Column('sale_price', sa.Numeric()),
        sa.Column('distance_meters', sa.Integer()),
        sa.Column('similarity_score', sa.Numeric()),
        sa.Column('raw_payload', sa.JSON()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('valuation_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_name', sa.Text(), nullable=False),
        sa.Column('model_version', sa.Text()),
        sa.Column('inputs', sa.JSON()),
        sa.Column('outputs', sa.JSON()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('risk_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title_risk', sa.Numeric()),
        sa.Column('flood_risk', sa.Numeric()),
        sa.Column('market_risk', sa.Numeric()),
        sa.Column('overall_confidence', sa.Numeric()),
        sa.Column('details', sa.JSON()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('agent_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('task_id', sa.Text(), nullable=False, unique=True),
        sa.Column('agent_name', sa.Text(), nullable=False),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='SET NULL')),
        sa.Column('run_mode', sa.Text()),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('log', sa.JSON()),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id')),
        sa.Column('request_id', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='SET NULL')),
        sa.Column('report_id', sa.Text(), nullable=False, unique=True),
        sa.Column('summary', sa.Text()),
        sa.Column('sections', sa.JSON()),
        sa.Column('confidence_overall', sa.Numeric()),
        sa.Column('generated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('decision', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('audit_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('event_time', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('payload', sa.JSON())
    )


def downgrade():
    op.drop_table('audit_logs')
    op.drop_table('approvals')
    op.drop_table('reports')
    op.drop_table('agent_tasks')
    op.drop_table('risk_scores')
    op.drop_table('valuation_models')
    op.drop_table('comps')
    op.drop_table('documents')
    op.drop_table('leases')
    op.drop_table('financials_history')
    op.drop_table('financials_last12mo')
    op.drop_table('provenance_entries')
    op.drop_table('property_source_ids')
    op.drop_table('properties')
    op.drop_table('users')

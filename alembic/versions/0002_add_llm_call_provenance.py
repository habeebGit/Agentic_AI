"""add llm_call_provenance table

Revision ID: 0002_add_llm_call_provenance
Revises: 0001_create_schema
Create Date: 2026-01-31 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002_add_llm_call_provenance'
down_revision = '0001_create_schema'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'llm_call_provenance',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('request_id', sa.Text(), nullable=True),
        sa.Column('model', sa.Text(), nullable=False),
        sa.Column('provider', sa.Text(), nullable=True),
        sa.Column('prompt', sa.Text()),
        sa.Column('response', sa.Text()),
        sa.Column('usage', sa.JSON()),
        sa.Column('property_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('properties.id', ondelete='SET NULL'), nullable=True),
        sa.Column('field_path', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Numeric(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )


def downgrade():
    op.drop_table('llm_call_provenance')

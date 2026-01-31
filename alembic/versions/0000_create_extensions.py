"""create extensions

Revision ID: 0000_create_extensions
Revises:
Create Date: 2026-01-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0000_create_extensions'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create required Postgres extensions. Requires superuser or proper privileges.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")


def downgrade():
    # Note: Dropping extensions may affect other DB objects. Use with caution.
    op.execute("DROP EXTENSION IF EXISTS btree_gin;")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
    op.execute("DROP EXTENSION IF EXISTS citext;")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")

"""Add fingerprint column for cross-source deduplication.

Revision ID: 002
Revises: 001
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("fingerprint", sa.String(64), nullable=True))
    op.create_index("ix_listings_fingerprint", "listings", ["fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_listings_fingerprint", table_name="listings")
    op.drop_column("listings", "fingerprint")

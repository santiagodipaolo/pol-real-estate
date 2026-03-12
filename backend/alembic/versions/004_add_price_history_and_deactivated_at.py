"""Add price history table and deactivated_at column.

Revision ID: 004
Revises: 003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listing_price_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("listing_id", UUID(as_uuid=True), sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("price_usd_blue", sa.Numeric(14, 2)),
        sa.Column("price_ars", sa.Numeric(14, 2)),
        sa.Column("currency_original", sa.String(3)),
        sa.Column("price_original", sa.Numeric(14, 2)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("source", sa.String(20), nullable=False, server_default="scrape"),
    )
    op.create_index("ix_listing_price_history_listing_id", "listing_price_history", ["listing_id"])

    op.add_column("listings", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "deactivated_at")
    op.drop_index("ix_listing_price_history_listing_id", table_name="listing_price_history")
    op.drop_table("listing_price_history")

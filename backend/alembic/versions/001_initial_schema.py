"""Initial schema

Revision ID: 001
Revises: None
Create Date: 2026-02-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "barrios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("comuna_id", sa.Integer(), nullable=False),
        sa.Column("comuna_name", sa.String(50)),
        sa.Column("geometry", JSONB),
        sa.Column("area_km2", sa.Numeric(10, 4)),
        sa.Column("centroid_lat", sa.Numeric(10, 7)),
        sa.Column("centroid_lon", sa.Numeric(10, 7)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "listings",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("canonical_id", UUID(as_uuid=True), nullable=True),
        sa.Column("url", sa.Text()),
        sa.Column("title", sa.Text()),
        sa.Column("operation_type", sa.String(20), nullable=False),
        sa.Column("property_type", sa.String(50), nullable=False),
        sa.Column("price_original", sa.Numeric(14, 2)),
        sa.Column("currency_original", sa.String(3)),
        sa.Column("price_usd_blue", sa.Numeric(14, 2)),
        sa.Column("price_usd_official", sa.Numeric(14, 2)),
        sa.Column("price_usd_mep", sa.Numeric(14, 2)),
        sa.Column("price_ars", sa.Numeric(14, 2)),
        sa.Column("expenses_ars", sa.Numeric(14, 2)),
        sa.Column("surface_total_m2", sa.Numeric(10, 2)),
        sa.Column("surface_covered_m2", sa.Numeric(10, 2)),
        sa.Column("rooms", sa.SmallInteger()),
        sa.Column("bedrooms", sa.SmallInteger()),
        sa.Column("bathrooms", sa.SmallInteger()),
        sa.Column("garages", sa.SmallInteger()),
        sa.Column("age_years", sa.SmallInteger()),
        sa.Column("amenities", JSONB),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("barrio_id", sa.Integer(), sa.ForeignKey("barrios.id")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("days_on_market", sa.Integer()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_listings_barrio_id", "listings", ["barrio_id"])
    op.create_index("idx_listings_operation_type", "listings", ["operation_type"])
    op.create_index("idx_listings_source_external", "listings", ["source", "external_id"])
    op.create_index("idx_listings_price_usd_blue", "listings", ["price_usd_blue"])
    op.create_index("idx_listings_first_seen", "listings", ["first_seen_at"])

    op.create_table(
        "currency_rates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("rate_type", sa.String(20), nullable=False),
        sa.Column("buy", sa.Numeric(12, 4)),
        sa.Column("sell", sa.Numeric(12, 4)),
        sa.Column("source", sa.String(50)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_currency_rates_type_date", "currency_rates", ["rate_type", "recorded_at"])

    op.create_table(
        "barrio_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("barrio_id", sa.Integer(), sa.ForeignKey("barrios.id"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("operation_type", sa.String(20), nullable=False),
        sa.Column("property_type", sa.String(50), nullable=True),
        sa.Column("listing_count", sa.Integer()),
        sa.Column("median_price_usd_m2", sa.Numeric(10, 2)),
        sa.Column("avg_price_usd_m2", sa.Numeric(10, 2)),
        sa.Column("p25_price_usd_m2", sa.Numeric(10, 2)),
        sa.Column("p75_price_usd_m2", sa.Numeric(10, 2)),
        sa.Column("avg_days_on_market", sa.Numeric(10, 1)),
        sa.Column("new_listings_7d", sa.Integer()),
        sa.Column("removed_listings_7d", sa.Integer()),
        sa.Column("rental_yield_estimate", sa.Numeric(6, 4)),
        sa.Column("usd_blue_rate", sa.Numeric(12, 4)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barrio_id", "snapshot_date", "operation_type", "property_type", name="uq_barrio_snapshot"),
    )


def downgrade() -> None:
    op.drop_table("barrio_snapshots")
    op.drop_table("currency_rates")
    op.drop_table("listings")
    op.drop_table("barrios")

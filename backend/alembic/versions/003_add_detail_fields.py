"""Add detail scraping fields: floor, orientation, condition, description, detail_scraped_at.

Revision ID: 003
Revises: 002
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("floor", sa.SmallInteger(), nullable=True))
    op.add_column("listings", sa.Column("orientation", sa.String(20), nullable=True))
    op.add_column("listings", sa.Column("condition", sa.String(30), nullable=True))
    op.add_column("listings", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "listings",
        sa.Column("detail_scraped_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("listings", "detail_scraped_at")
    op.drop_column("listings", "description")
    op.drop_column("listings", "condition")
    op.drop_column("listings", "orientation")
    op.drop_column("listings", "floor")

"""Add Selenium scraping fields.

Revision ID: 20260619_0002
Revises: 20260619_0001
Create Date: 2026-06-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260619_0002"
down_revision: Union[str, None] = "20260619_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("locations", sa.Column("google_maps_url", sa.Text()))
    op.add_column("locations", sa.Column("google_reviews_url", sa.Text()))
    op.add_column(
        "locations",
        sa.Column(
            "target_review_count",
            sa.Integer(),
            server_default="100",
            nullable=False,
        ),
    )

    op.add_column("reviews", sa.Column("reviewer_profile_url", sa.Text()))
    op.add_column("reviews", sa.Column("reviewer_photo_url", sa.Text()))
    op.add_column(
        "reviews",
        sa.Column("reviewer_local_guide_level", sa.String(length=100)),
    )
    op.add_column("reviews", sa.Column("reviewer_total_reviews", sa.Integer()))
    op.add_column(
        "reviews", sa.Column("review_relative_time", sa.String(length=100))
    )
    op.add_column(
        "reviews", sa.Column("review_language", sa.String(length=20))
    )
    op.add_column(
        "reviews",
        sa.Column("like_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("reviews", sa.Column("owner_response_text", sa.Text()))
    op.add_column(
        "reviews", sa.Column("owner_response_time", sa.DateTime(timezone=True))
    )
    op.add_column(
        "reviews", sa.Column("scraped_at", sa.DateTime(timezone=True))
    )

    op.add_column(
        "fetch_logs",
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("fetch_logs", "metadata")
    op.drop_column("reviews", "scraped_at")
    op.drop_column("reviews", "owner_response_time")
    op.drop_column("reviews", "owner_response_text")
    op.drop_column("reviews", "like_count")
    op.drop_column("reviews", "review_language")
    op.drop_column("reviews", "review_relative_time")
    op.drop_column("reviews", "reviewer_total_reviews")
    op.drop_column("reviews", "reviewer_local_guide_level")
    op.drop_column("reviews", "reviewer_photo_url")
    op.drop_column("reviews", "reviewer_profile_url")
    op.drop_column("locations", "target_review_count")
    op.drop_column("locations", "google_reviews_url")
    op.drop_column("locations", "google_maps_url")


"""Initial Hermina Review Intelligence schema.

Revision ID: 20260619_0001
Revises:
Create Date: 2026-06-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260619_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hospital_name", sa.String(length=150), nullable=False),
        sa.Column("branch_name", sa.String(length=150), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("external_place_id", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source", "external_place_id", name="uq_locations_source_place"
        ),
    )
    op.create_index("idx_locations_active", "locations", ["is_active"])
    op.create_index(
        "idx_locations_source_place",
        "locations",
        ["source", "external_place_id"],
    )

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("external_place_id", sa.String(length=255), nullable=True),
        sa.Column("external_review_id", sa.String(length=255), nullable=True),
        sa.Column("reviewer_name", sa.String(length=255), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column(
            "review_text", sa.Text(), server_default="", nullable=False
        ),
        sa.Column("review_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("review_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)",
            name="ck_reviews_rating",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_hash"),
    )
    op.create_index("idx_reviews_location_id", "reviews", ["location_id"])
    op.create_index("idx_reviews_rating", "reviews", ["rating"])
    op.create_index("idx_reviews_review_hash", "reviews", ["review_hash"])
    op.create_index("idx_reviews_review_time", "reviews", ["review_time"])
    op.create_index(
        "idx_reviews_source_place", "reviews", ["source", "external_place_id"]
    )

    op.create_table(
        "fetch_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column(
            "total_fetched", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "total_inserted", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "total_duplicate", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "total_failed", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_fetch_logs_location_id", "fetch_logs", ["location_id"])
    op.create_index("idx_fetch_logs_started_at", "fetch_logs", ["started_at"])
    op.create_index("idx_fetch_logs_status", "fetch_logs", ["status"])

    op.create_table(
        "review_analysis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("sentiment", sa.String(length=50), nullable=True),
        sa.Column(
            "sentiment_score", sa.Numeric(precision=5, scale=4), nullable=True
        ),
        sa.Column("issue_category", sa.String(length=100), nullable=True),
        sa.Column("urgency", sa.String(length=50), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column(
            "keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "is_potential_viral",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "is_patient_safety_issue",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column(
            "raw_response",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["review_id"], ["reviews.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_review_analysis_issue_category",
        "review_analysis",
        ["issue_category"],
    )
    op.create_index(
        "idx_review_analysis_review_id", "review_analysis", ["review_id"]
    )
    op.create_index(
        "idx_review_analysis_sentiment", "review_analysis", ["sentiment"]
    )
    op.create_index(
        "idx_review_analysis_urgency", "review_analysis", ["urgency"]
    )


def downgrade() -> None:
    op.drop_table("review_analysis")
    op.drop_table("fetch_logs")
    op.drop_table("reviews")
    op.drop_table("locations")


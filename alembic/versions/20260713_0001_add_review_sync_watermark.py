"""add reviews.sync_updated_at watermark + keyset index

Revision ID: 20260713_0001
Revises: 495376efebcb
Create Date: 2026-07-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260713_0001"
down_revision: Union[str, None] = "495376efebcb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Added nullable so the backfill can run before the NOT NULL is enforced;
    # adding it NOT NULL outright would stamp every existing row with now(),
    # which would tell OneBox that the entire table changed today.
    op.add_column(
        "reviews",
        sa.Column("sync_updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Same expression the CS-01 projection computed on the fly, so the values
    # OneBox has already seen stay identical across this migration.
    op.execute(
        """
        UPDATE reviews AS r
        SET sync_updated_at = GREATEST(
            r.updated_at,
            r.created_at,
            COALESCE(
                (
                    SELECT MAX(a.created_at)
                    FROM review_analysis AS a
                    WHERE a.review_id = r.id
                ),
                r.created_at
            )
        )
        """
    )

    op.alter_column(
        "reviews",
        "sync_updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )

    op.create_index(
        "idx_reviews_company_sync_id",
        "reviews",
        ["company_id", "sync_updated_at", "id"],
    )


def downgrade() -> None:
    # Drops the cursor capability: every cursor OneBox holds becomes unusable, so
    # this only runs alongside an application rollback and a consumer re-bootstrap.
    op.drop_index("idx_reviews_company_sync_id", table_name="reviews")
    op.drop_column("reviews", "sync_updated_at")

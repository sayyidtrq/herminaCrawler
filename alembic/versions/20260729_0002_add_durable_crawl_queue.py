"""add durable crawl queue

Revision ID: 20260729_0002
Revises: 20260724_0001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0002"
down_revision: Union[str, None] = "20260724_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_locations_id_company", "locations", ["id", "company_id"]
    )
    op.create_table(
        "crawl_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by_client_id",
            sa.Integer(),
            sa.ForeignKey("api_clients.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("slot", sa.String(length=50), nullable=True),
        sa.Column(
            "status", sa.String(length=30), nullable=False, server_default="queued"
        ),
        sa.Column(
            "analyze_after_crawl",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "company_id", "idempotency_key", name="uq_crawl_batches_company_idempotency"
        ),
    )
    op.create_index(
        "idx_crawl_batches_public_id", "crawl_batches", ["public_id"], unique=True
    )
    op.create_index(
        "idx_crawl_batches_company_created",
        "crawl_batches",
        ["company_id", "created_at"],
    )
    op.create_table(
        "crawl_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "batch_id",
            sa.Integer(),
            sa.ForeignKey("crawl_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("onebox_location_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=30), nullable=False, server_default="queued"
        ),
        sa.Column("source_snapshot", sa.String(length=50), nullable=False),
        sa.Column("target_review_count", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "result_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "batch_id", "location_id", name="uq_crawl_jobs_batch_location"
        ),
        sa.ForeignKeyConstraint(
            ["location_id", "company_id"],
            ["locations.id", "locations.company_id"],
            name="fk_crawl_jobs_location_tenant",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "idx_crawl_jobs_claim",
        "crawl_jobs",
        ["status", "available_at", "lease_expires_at"],
    )
    op.create_index("idx_crawl_jobs_company", "crawl_jobs", ["company_id"])


def downgrade() -> None:
    op.drop_index("idx_crawl_jobs_company", table_name="crawl_jobs")
    op.drop_index("idx_crawl_jobs_claim", table_name="crawl_jobs")
    op.drop_table("crawl_jobs")
    op.drop_index("idx_crawl_batches_company_created", table_name="crawl_batches")
    op.drop_index("idx_crawl_batches_public_id", table_name="crawl_batches")
    op.drop_table("crawl_batches")
    op.drop_constraint("uq_locations_id_company", "locations", type_="unique")

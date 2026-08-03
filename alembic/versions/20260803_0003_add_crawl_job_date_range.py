"""tambah rentang tanggal pada crawl_jobs

Revision ID: 20260803_0003
Revises: 20260729_0002
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

revision = "20260803_0003"
down_revision = "20260729_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crawl_jobs", sa.Column("date_from", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "crawl_jobs", sa.Column("date_to", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("crawl_jobs", "date_to")
    op.drop_column("crawl_jobs", "date_from")

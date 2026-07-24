"""add OneBox worklist cache and sync state

Revision ID: 20260724_0001
Revises: 20260713_0002
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260724_0001"
down_revision: Union[str, None] = "20260713_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("locations", sa.Column("onebox_connection_id", sa.Integer(), nullable=True))
    op.add_column("locations", sa.Column("onebox_location_id", sa.Integer(), nullable=True))
    op.add_column("locations", sa.Column("crawl_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("locations", sa.Column("ingest_reviews", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("locations", sa.Column("is_mock", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("locations", sa.Column("worklist_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("idx_locations_onebox_connection", "locations", ["onebox_connection_id"])

    op.add_column("competitors", sa.Column("onebox_connection_id", sa.Integer(), nullable=True))
    op.add_column("competitors", sa.Column("onebox_location_id", sa.Integer(), nullable=True))
    op.add_column("competitors", sa.Column("crawl_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("competitors", sa.Column("ingest_reviews", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("competitors", sa.Column("is_mock", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("competitors", sa.Column("worklist_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("idx_competitors_onebox_connection", "competitors", ["onebox_connection_id"])

    op.create_table(
        "worklist_sync_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("company_id", name="uq_worklist_sync_states_company"),
    )
    op.create_index("idx_worklist_sync_states_company", "worklist_sync_states", ["company_id"])


def downgrade() -> None:
    op.drop_index("idx_worklist_sync_states_company", table_name="worklist_sync_states")
    op.drop_table("worklist_sync_states")
    op.drop_index("idx_competitors_onebox_connection", table_name="competitors")
    for column in ("worklist_synced_at", "is_mock", "ingest_reviews", "crawl_enabled", "onebox_location_id", "onebox_connection_id"):
        op.drop_column("competitors", column)
    op.drop_index("idx_locations_onebox_connection", table_name="locations")
    for column in ("worklist_synced_at", "is_mock", "ingest_reviews", "crawl_enabled", "onebox_location_id", "onebox_connection_id"):
        op.drop_column("locations", column)

"""Initial schema for RecAI models.

Revision ID: 0001_init_models
Revises:
Create Date: 2024-01-01 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_init_models"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("genres", sa.String(length=256), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "interactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "event_type IN ('view', 'click', 'rate')",
            name="ck_interactions_event_type",
        ),
    )

    op.create_index("ix_interactions_user_ts", "interactions", ["user_id", "ts"])
    op.create_index("ix_interactions_item_ts", "interactions", ["item_id", "ts"])
    op.create_index("ix_interactions_user_item", "interactions", ["user_id", "item_id"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("trained_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
    )


def downgrade() -> None:
    op.drop_table("model_versions")
    op.drop_index("ix_interactions_user_item", table_name="interactions")
    op.drop_index("ix_interactions_item_ts", table_name="interactions")
    op.drop_index("ix_interactions_user_ts", table_name="interactions")
    op.drop_table("interactions")
    op.drop_table("items")
    op.drop_table("users")
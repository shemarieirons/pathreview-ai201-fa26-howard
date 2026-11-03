"""Add review_share_links table for public share tokens.

Revision ID: 003
Revises: 002
Create Date: 2026-11-02 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore[attr-defined]

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_share_links",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("review_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["review_id"],
            ["reviews.id"],
            name=op.f("fk_review_share_links_review_id_reviews"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_share_links")),
        sa.UniqueConstraint("token", name=op.f("uq_review_share_links_token")),
    )
    op.create_index(op.f("ix_review_share_links_token"), "review_share_links", ["token"])
    op.create_index(op.f("ix_review_share_links_review_id"), "review_share_links", ["review_id"])
    op.create_index(op.f("ix_review_share_links_expires_at"), "review_share_links", ["expires_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_review_share_links_expires_at"), table_name="review_share_links")
    op.drop_index(op.f("ix_review_share_links_review_id"), table_name="review_share_links")
    op.drop_index(op.f("ix_review_share_links_token"), table_name="review_share_links")
    op.drop_table("review_share_links")

"""Add password credentials for account authentication.

Revision ID: 20261023_auth_credentials
Revises: 45bc4de57763
Create Date: 2026-10-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261023_auth_credentials"
down_revision: Union[str, None] = "45bc4de57763"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_auth_credentials_user_id"),
    )
    op.create_index("ix_auth_credentials_user_id", "auth_credentials", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_auth_credentials_user_id", table_name="auth_credentials")
    op.drop_table("auth_credentials")

"""add email column to users

Revision ID: 2a3b4c5d6e7f
Revises: dc65e9ede111
Create Date: 2026-06-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2a3b4c5d6e7f"
down_revision: Union[str, Sequence[str], None] = "dc65e9ede111"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "email")

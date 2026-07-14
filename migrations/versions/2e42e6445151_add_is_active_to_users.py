"""add is_active to users

Revision ID: 2e42e6445151
Revises: 781d654a6975
Create Date: 2026-07-14 15:33:29.436007

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2e42e6445151'
down_revision: Union[str, Sequence[str], None] = '781d654a6975'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_active')

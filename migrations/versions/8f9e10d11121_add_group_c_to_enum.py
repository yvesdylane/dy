"""add group C to enum

Revision ID: 8f9e10d11121
Revises: 2e42e6445151
Create Date: 2026-07-14 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8f9e10d11121'
down_revision: Union[str, Sequence[str], None] = '2e42e6445151'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('group',
            existing_type=sa.Enum('A', 'B', name='group'),
            type_=sa.Enum('A', 'B', 'C', name='group'),
            existing_nullable=True)

    with op.batch_alter_table('attendances', schema=None) as batch_op:
        batch_op.alter_column('group',
            existing_type=sa.Enum('A', 'B', name='group'),
            type_=sa.Enum('A', 'B', 'C', name='group'),
            existing_nullable=False)

    with op.batch_alter_table('user_complains', schema=None) as batch_op:
        batch_op.alter_column('group',
            existing_type=sa.Enum('A', 'B', name='group'),
            type_=sa.Enum('A', 'B', 'C', name='group'),
            existing_nullable=True)

    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.alter_column('group',
            existing_type=sa.Enum('A', 'B', name='group'),
            type_=sa.Enum('A', 'B', 'C', name='group'),
            existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.alter_column('group',
            existing_type=sa.Enum('A', 'B', 'C', name='group'),
            type_=sa.Enum('A', 'B', name='group'),
            existing_nullable=True)

    with op.batch_alter_table('user_complains', schema=None) as batch_op:
        batch_op.alter_column('group',
            existing_type=sa.Enum('A', 'B', 'C', name='group'),
            type_=sa.Enum('A', 'B', name='group'),
            existing_nullable=True)

    with op.batch_alter_table('attendances', schema=None) as batch_op:
        batch_op.alter_column('group',
            existing_type=sa.Enum('A', 'B', 'C', name='group'),
            type_=sa.Enum('A', 'B', name='group'),
            existing_nullable=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('group',
            existing_type=sa.Enum('A', 'B', 'C', name='group'),
            type_=sa.Enum('A', 'B', name='group'),
            existing_nullable=True)

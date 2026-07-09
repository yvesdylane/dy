"""drop_cleaning_tables

Revision ID: fc7330f8914c
Revises: b3bc8c240343
Create Date: 2026-07-07 03:05:41.744288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc7330f8914c'
down_revision: Union[str, Sequence[str], None] = 'b3bc8c240343'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('cleaning_completions')
    op.drop_table('cleaning_group_members')
    op.drop_table('cleaning_duties')
    op.drop_table('cleaning_groups')


def downgrade() -> None:
    op.create_table('cleaning_groups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('department', sa.Enum('ISM', 'SWE', 'CGWD', 'EDM', 'DBMS', 'CSN', 'NWS', name='department'), nullable=False),
        sa.Column('turn_order', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('cleaning_duties',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['cleaning_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('cleaning_group_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('cycle_cleaned', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['cleaning_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('cleaning_completions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('duty_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['duty_id'], ['cleaning_duties.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

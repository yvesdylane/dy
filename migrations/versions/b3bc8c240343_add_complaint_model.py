"""add_complaint_model

Revision ID: b3bc8c240343
Revises: 2a3b4c5d6e7f
Create Date: 2026-07-05 19:28:49.837445

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3bc8c240343'
down_revision: Union[str, Sequence[str], None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('complaints',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('complain_type', sa.Enum('complaint', 'advice', name='complaintype'), nullable=False),
        sa.Column('department', sa.Enum('ISM', 'SWE', 'CGWD', 'EDM', 'CSN', 'DBMS', 'NWS', name='department'), nullable=False),
        sa.Column('group', sa.Enum('A', 'B', name='group'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('complaints')

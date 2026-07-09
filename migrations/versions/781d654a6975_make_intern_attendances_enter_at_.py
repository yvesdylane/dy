"""make intern_attendances.enter_at nullable

Revision ID: 781d654a6975
Revises: fc7330f8914c
Create Date: 2026-07-09 11:54:09.399524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '781d654a6975'
down_revision: Union[str, Sequence[str], None] = 'fc7330f8914c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('intern_attendances', schema=None) as batch_op:
        batch_op.alter_column('enter_at',
               existing_type=sa.DATETIME(),
               nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('intern_attendances', schema=None) as batch_op:
        batch_op.alter_column('enter_at',
               existing_type=sa.DATETIME(),
               nullable=False)

"""add subject no_repeat_same_day and max_concurrent_sessions

Revision ID: 2673d3e83d1c
Revises: af80d1356b42
Create Date: 2026-07-16 14:49:58.782824

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2673d3e83d1c'
down_revision: Union[str, Sequence[str], None] = 'af80d1356b42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('subjects') as batch_op:
        batch_op.add_column(
            sa.Column('no_repeat_same_day', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column('max_concurrent_sessions', sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('subjects') as batch_op:
        batch_op.drop_column('max_concurrent_sessions')
        batch_op.drop_column('no_repeat_same_day')

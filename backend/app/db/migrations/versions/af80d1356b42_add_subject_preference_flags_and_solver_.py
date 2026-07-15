"""add subject preference flags and solver weight columns

Revision ID: af80d1356b42
Revises: a3f9c1d02b4e
Create Date: 2026-07-15 13:40:53.683705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af80d1356b42'
down_revision: Union[str, Sequence[str], None] = 'a3f9c1d02b4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('subjects') as batch_op:
        batch_op.add_column(
            sa.Column('prefer_early_periods', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column('avoid_friday_afternoon', sa.Boolean(), nullable=False, server_default=sa.false())
        )
    with op.batch_alter_table('solver_settings') as batch_op:
        batch_op.add_column(
            sa.Column('weight_prefer_early_periods', sa.Integer(), nullable=False, server_default='10')
        )
        batch_op.add_column(
            sa.Column('weight_avoid_friday_afternoon', sa.Integer(), nullable=False, server_default='10')
        )


def downgrade() -> None:
    with op.batch_alter_table('solver_settings') as batch_op:
        batch_op.drop_column('weight_avoid_friday_afternoon')
        batch_op.drop_column('weight_prefer_early_periods')
    with op.batch_alter_table('subjects') as batch_op:
        batch_op.drop_column('avoid_friday_afternoon')
        batch_op.drop_column('prefer_early_periods')

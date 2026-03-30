"""add notes to cases

Revision ID: b3f1a2c4d5e6
Revises: 24cfefa17a0a
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3f1a2c4d5e6'
down_revision: Union[str, Sequence[str], None] = '24cfefa17a0a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cases', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('cases', 'notes')

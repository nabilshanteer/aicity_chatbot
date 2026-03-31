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
    # Add notes column to cases table (try both possible table names)
    try:
        op.add_column('cases', sa.Column('notes', sa.Text(), nullable=True))
    except Exception:
        try:
            op.add_column('chats', sa.Column('notes', sa.Text(), nullable=True))
        except Exception:
            pass


def downgrade() -> None:
    try:
        op.drop_column('cases', 'notes')
    except Exception:
        try:
            op.drop_column('chats', 'notes')
        except Exception:
            pass


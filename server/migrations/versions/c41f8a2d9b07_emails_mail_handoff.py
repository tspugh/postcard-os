"""emails mail handoff — approved versions handed into the operator's mailbox as drafts

Revision ID: c41f8a2d9b07
Revises: a023241cbaab
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c41f8a2d9b07'
down_revision: Union[str, None] = 'a023241cbaab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('emails', sa.Column('delivery_provider', sa.Text(), nullable=True))
    op.add_column('emails', sa.Column('provider_draft_id', sa.Text(), nullable=True))
    op.add_column('emails', sa.Column('handed_off_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('emails', 'handed_off_at')
    op.drop_column('emails', 'provider_draft_id')
    op.drop_column('emails', 'delivery_provider')

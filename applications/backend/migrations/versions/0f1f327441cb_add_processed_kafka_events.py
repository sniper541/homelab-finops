"""add processed kafka events

Revision ID: 0f1f327441cb
Revises: 48a748f18ee9
Create Date: 2026-09-28 13:37:50.581782

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f1f327441cb'
down_revision: Union[str, Sequence[str], None] = '48a748f18ee9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
    "processed_kafka_events",
    sa.Column("event_id", sa.String(length=64), nullable=False),
    sa.Column(
        "processed_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    ),
    sa.PrimaryKeyConstraint("event_id"),
    ) 
    pass


def downgrade() -> None:
    op.drop_table("processed_kafka_events")
    pass

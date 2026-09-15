"""add keycloak sub to users

Revision ID: 48a748f18ee9
Revises: 4d68481b1a7f
Create Date: 2026-09-14 14:01:37.155777
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "48a748f18ee9"
down_revision: Union[str, Sequence[str], None] = "4d68481b1a7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Keycloak user identity to FinOps users."""

    op.add_column(
        "users",
        sa.Column(
            "keycloak_sub",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.create_unique_constraint(
        "uq_users_keycloak_sub",
        "users",
        ["keycloak_sub"],
    )


def downgrade() -> None:
    """Remove Keycloak user identity from FinOps users."""

    op.drop_constraint(
        "uq_users_keycloak_sub",
        "users",
        type_="unique",
    )

    op.drop_column(
        "users",
        "keycloak_sub",
    )

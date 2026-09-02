"""create initial finops data model

Revision ID: 4d68481b1a7f
Revises: 44640283e7f4
Create Date: 2026-09-02 12:10:06.888973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d68481b1a7f'
down_revision: Union[str, Sequence[str], None] = '44640283e7f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial FinOps data model."""

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("icon", sa.String(length=32), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_categories_user_id_users",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "type IN ('income', 'expense')",
            name="ck_categories_type",
        ),
        sa.UniqueConstraint(
            "user_id",
            "type",
            "name",
            name="uq_categories_user_type_name",
        ),
        sa.UniqueConstraint(
            "id",
            "user_id",
            name="uq_categories_id_user_id",
        ),
    )

    op.drop_table("transactions")

    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_transactions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_transactions_category_user",
        ),
        sa.CheckConstraint(
            "amount > 0",
            name="ck_transactions_amount_positive",
        ),
    )

    op.create_index(
        "ix_transactions_user_occurred_at",
        "transactions",
        ["user_id", "occurred_at"],
    )

    op.create_index(
        "ix_transactions_user_category_occurred_at",
        "transactions",
        ["user_id", "category_id", "occurred_at"],
    )

    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "default_currency",
            sa.String(length=3),
            nullable=False,
            server_default="RUB",
        ),
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Europe/Moscow",
        ),
        sa.Column(
            "language",
            sa.String(length=10),
            nullable=False,
            server_default="ru",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_settings_user_id_users",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    """Downgrade initial FinOps data model."""

    op.drop_table("user_settings")

    op.drop_index(
        "ix_transactions_user_category_occurred_at",
        table_name="transactions",
    )

    op.drop_index(
        "ix_transactions_user_occurred_at",
        table_name="transactions",
    )

    op.drop_table("transactions")
    op.drop_table("categories")
    op.drop_table("users")

    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
    )

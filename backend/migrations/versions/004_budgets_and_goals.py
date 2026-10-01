"""Add account-scoped budgets and savings goals.

Revision ID: 004_budgets_and_goals
Revises: 003_transaction_metadata
"""
from alembic import op
import sqlalchemy as sa

revision = "004_budgets_and_goals"
down_revision = "003_transaction_metadata"


def upgrade():
    inspector = sa.inspect(op.get_bind())
    budget_columns = {column["name"] for column in inspector.get_columns("budgets")}
    if "wallet_id" not in budget_columns:
        op.add_column("budgets", sa.Column("wallet_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_budgets_wallet_id", "budgets", "wallets", ["wallet_id"], ["id"], ondelete="CASCADE")
    if "threshold_percent" not in budget_columns:
        op.add_column("budgets", sa.Column("threshold_percent", sa.Integer(), nullable=False, server_default="75"))
    if "goals" not in inspector.get_table_names():
        op.create_table(
            "goals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("linked_wallet_id", sa.Integer(), sa.ForeignKey("wallets.id", ondelete="SET NULL"), nullable=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("target_amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("current_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("target_date", sa.Date(), nullable=True),
            sa.Column("monthly_contribution", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_goals_user_id", "goals", ["user_id"])


def downgrade():
    op.drop_index("ix_goals_user_id", table_name="goals")
    op.drop_table("goals")
    op.drop_constraint("fk_budgets_wallet_id", "budgets", type_="foreignkey")
    op.drop_column("budgets", "wallet_id")
    op.drop_column("budgets", "threshold_percent")

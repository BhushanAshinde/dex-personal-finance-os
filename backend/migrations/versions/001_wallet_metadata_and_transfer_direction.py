"""Add wallet metadata and transfer direction.

Revision ID: 001_wallet_metadata
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "001_wallet_metadata"
down_revision = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    wallet_columns = {column["name"] for column in inspector.get_columns("wallets")}
    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
    wallet_additions = {
        "bank_name": sa.Column("bank_name", sa.String(length=120), nullable=True),
        "account_last4": sa.Column("account_last4", sa.String(length=4), nullable=True),
        "account_holder_name": sa.Column("account_holder_name", sa.String(length=120), nullable=True),
        "currency": sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        "description": sa.Column("description", sa.String(length=500), nullable=True),
        "opening_balance": sa.Column("opening_balance", sa.Numeric(14, 2), nullable=False, server_default="0"),
        "is_default": sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        "updated_at": sa.Column("updated_at", sa.DateTime(), nullable=True),
    }
    transaction_additions = {
        "transfer_id": sa.Column("transfer_id", sa.String(length=36), nullable=True),
        "transfer_direction": sa.Column("transfer_direction", sa.String(length=3), nullable=True),
    }
    for name, column in wallet_additions.items():
        if name not in wallet_columns: op.add_column("wallets", column)
    for name, column in transaction_additions.items():
        if name not in transaction_columns: op.add_column("transactions", column)
    if "ix_transactions_transfer_id" not in {index["name"] for index in inspector.get_indexes("transactions")}:
        op.create_index("ix_transactions_transfer_id", "transactions", ["transfer_id"])


def downgrade():
    op.drop_index("ix_transactions_transfer_id", table_name="transactions")
    op.drop_column("transactions", "transfer_direction")
    op.drop_column("transactions", "transfer_id")
    op.drop_column("wallets", "updated_at")
    op.drop_column("wallets", "is_default")
    op.drop_column("wallets", "opening_balance")
    op.drop_column("wallets", "description")
    op.drop_column("wallets", "currency")
    op.drop_column("wallets", "account_holder_name")
    op.drop_column("wallets", "account_last4")
    op.drop_column("wallets", "bank_name")

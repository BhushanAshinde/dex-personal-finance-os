"""Add transaction reference and update timestamps.

Revision ID: 003_transaction_metadata
Revises: 002_user_profiles
"""
from alembic import op
import sqlalchemy as sa

revision = "003_transaction_metadata"
down_revision = "002_user_profiles"


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("transactions")}
    if "reference_number" not in columns:
        op.add_column("transactions", sa.Column("reference_number", sa.String(length=100), nullable=True))
    if "updated_at" not in columns:
        op.add_column("transactions", sa.Column("updated_at", sa.DateTime(), nullable=True))
    if "ix_transactions_reference_number" not in {index["name"] for index in inspector.get_indexes("transactions")}:
        op.create_index("ix_transactions_reference_number", "transactions", ["reference_number"])


def downgrade():
    op.drop_index("ix_transactions_reference_number", table_name="transactions")
    op.drop_column("transactions", "updated_at")
    op.drop_column("transactions", "reference_number")

"""Add user profiles, activation, and roles.

Revision ID: 002_user_profiles
Revises: 001_wallet_metadata
"""
from alembic import op
import sqlalchemy as sa

revision = "002_user_profiles"
down_revision = "001_wallet_metadata"


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    additions = {
        "full_name": sa.Column("full_name", sa.String(length=120), nullable=False, server_default="User"),
        "role": sa.Column("role", sa.String(length=20), nullable=False, server_default="USER"),
        "is_active": sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        "profile_picture": sa.Column("profile_picture", sa.String(length=500), nullable=True),
        "currency": sa.Column("currency", sa.String(length=3), nullable=False, server_default="INR"),
        "timezone": sa.Column("timezone", sa.String(length=80), nullable=False, server_default="Asia/Kolkata"),
        "date_format": sa.Column("date_format", sa.String(length=30), nullable=False, server_default="DD-MM-YYYY"),
        "last_login": sa.Column("last_login", sa.DateTime(), nullable=True),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("users", column)
    if "ix_users_role" not in {index["name"] for index in inspector.get_indexes("users")}:
        op.create_index("ix_users_role", "users", ["role"])
    if "ix_users_is_active" not in {index["name"] for index in inspector.get_indexes("users")}:
        op.create_index("ix_users_is_active", "users", ["is_active"])


def downgrade():
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    for name in ["last_login", "date_format", "timezone", "currency", "profile_picture", "is_active", "role", "full_name"]:
        op.drop_column("users", name)

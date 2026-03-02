"""add local auth password hash"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_local_auth"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.execute("UPDATE users SET auth_provider = 'password' WHERE auth_provider IS NULL OR auth_provider = 'clerk'")


def downgrade() -> None:
    op.drop_column("users", "password_hash")

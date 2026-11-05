"""report status check

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05 17:42:40.086101
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # autogenerate가 CHECK 제약을 감지하지 못해 직접 작성
    op.create_check_constraint(
        "ck_reports_status",
        "reports",
        "status IN ('PENDING', 'ANALYZING', 'COMPLETED', 'FAILED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_reports_status", "reports", type_="check")

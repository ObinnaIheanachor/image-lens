"""initial schema

Revision ID: 20260421_0001
Revises:
Create Date: 2026-04-21 00:00:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260421_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "jobs" not in existing_tables:
        op.create_table(
            "jobs",
            sa.Column("id", sa.String(length=40), primary_key=True, nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("image_path", sa.Text(), nullable=False),
            sa.Column("image_sha256", sa.String(length=64), nullable=False),
            sa.Column("image_mime", sa.String(length=50), nullable=False),
            sa.Column("image_bytes", sa.Integer(), nullable=True),
            sa.Column("image_width", sa.Integer(), nullable=True),
            sa.Column("image_height", sa.Integer(), nullable=True),
            sa.Column("idempotency_key", sa.String(length=255), nullable=True),
            sa.Column("webhook_url", sa.Text(), nullable=True),
            sa.Column("user_metadata_json", sa.Text(), nullable=True),
            sa.Column("report_id", sa.String(length=40), nullable=True),
            sa.Column("error_code", sa.String(length=50), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_jobs_status", "jobs", ["status"])
        op.create_index("ix_jobs_image_sha256", "jobs", ["image_sha256"])
        op.create_index("ix_jobs_idempotency_key", "jobs", ["idempotency_key"])

    if "reports" not in existing_tables:
        op.create_table(
            "reports",
            sa.Column("id", sa.String(length=40), primary_key=True, nullable=False),
            sa.Column("job_id", sa.String(length=40), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_reports_job_id", "reports", ["job_id"])

    # Ensure legacy databases allow GDPR nulling behavior.
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE reports ALTER COLUMN payload_json DROP NOT NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "reports" in existing_tables:
        op.drop_index("ix_reports_job_id", table_name="reports")
        op.drop_table("reports")
    if "jobs" in existing_tables:
        op.drop_index("ix_jobs_idempotency_key", table_name="jobs")
        op.drop_index("ix_jobs_image_sha256", table_name="jobs")
        op.drop_index("ix_jobs_status", table_name="jobs")
        op.drop_table("jobs")

"""Add daily reopen state; tolerate schema created by the old initial migration."""
from alembic import op
import sqlalchemy as sa

revision = "0002_daily_reopen_audit"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("daily_reports")}
    if "is_reopened" not in columns:
        # SQLite supports this additive ALTER directly; no table copy/reordering.
        op.add_column("daily_reports", sa.Column(
            "is_reopened", sa.Boolean(), nullable=False, server_default=sa.text("0"),
        ))

    if not sa.inspect(bind).has_table("daily_report_reopen_audits"):
        op.create_table(
            "daily_report_reopen_audits",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("daily_report_id", sa.Integer(), sa.ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reopened_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=False),
        )

    # The broken 0001 may have created these indexes with ORM-generated names.
    indexed_columns = {
        tuple(index["column_names"])
        for index in sa.inspect(bind).get_indexes("daily_report_reopen_audits")
    }
    for name, column in (
        ("ix_daily_reopen_report", "daily_report_id"),
        ("ix_daily_reopen_admin", "reopened_by"),
        ("ix_daily_reopen_time", "reopened_at"),
    ):
        if (column,) not in indexed_columns:
            op.create_index(name, "daily_report_reopen_audits", [column])
    if bind.dialect.name == "sqlite":
        op.execute("PRAGMA optimize")


def downgrade():
    # Dropping the table removes indexes regardless of their historical names.
    op.drop_table("daily_report_reopen_audits")
    with op.batch_alter_table("daily_reports") as batch_op:
        batch_op.drop_column("is_reopened")

"""add daily reopen state and audit history"""
from alembic import op
import sqlalchemy as sa

revision="0002_daily_reopen_audit"
down_revision="0001_initial"
branch_labels=None
depends_on=None

def upgrade():
    with op.batch_alter_table("daily_reports") as batch_op:
        batch_op.add_column(sa.Column("is_reopened",sa.Boolean(),nullable=False,server_default=sa.false()))
    op.create_table(
        "daily_report_reopen_audits",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("daily_report_id",sa.Integer(),sa.ForeignKey("daily_reports.id",ondelete="CASCADE"),nullable=False),
        sa.Column("reopened_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
        sa.Column("reason",sa.Text(),nullable=False),
        sa.Column("reopened_at",sa.DateTime(timezone=True),nullable=False),
    )
    op.create_index("ix_daily_reopen_report","daily_report_reopen_audits",["daily_report_id"])
    op.create_index("ix_daily_reopen_admin","daily_report_reopen_audits",["reopened_by"])
    op.create_index("ix_daily_reopen_time","daily_report_reopen_audits",["reopened_at"])

def downgrade():
    op.drop_index("ix_daily_reopen_time",table_name="daily_report_reopen_audits")
    op.drop_index("ix_daily_reopen_admin",table_name="daily_report_reopen_audits")
    op.drop_index("ix_daily_reopen_report",table_name="daily_report_reopen_audits")
    op.drop_table("daily_report_reopen_audits")
    with op.batch_alter_table("daily_reports") as batch_op:
        batch_op.drop_column("is_reopened")

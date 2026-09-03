"""Frozen initial schema, independent of current application models."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def initial_schema():
    metadata = sa.MetaData()

    def timestamps():
        return [
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        ]

    sa.Table(
        "users", metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("ADMIN", "MEMBER", name="role"), nullable=False, index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, index=True),
        *timestamps(),
    )
    sa.Table(
        "user_stories", metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True, index=True),
        sa.Column("title", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.Enum("TODO", "IN_PROGRESS", "BLOCKED", "DONE", "CLOSED", name="storystatus"), nullable=False, index=True),
        sa.Column("priority", sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="priority"), nullable=False, index=True),
        sa.Column("start_date", sa.Date()),
        sa.Column("due_date", sa.Date(), index=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    sa.Table(
        "user_story_assignments", metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_story_id", sa.Integer(), sa.ForeignKey("user_stories.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_story_id", "user_id", name="uq_story_user"),
    )
    sa.Table(
        "daily_reports", metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("report_date", sa.Date(), nullable=False, index=True),
        sa.Column("general_note", sa.Text()),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.Enum("DRAFT", "SUBMITTED", name="dailystatus"), nullable=False, index=True),
        *timestamps(),
        sa.UniqueConstraint("user_id", "report_date", name="uq_daily_user_date"),
        sa.Index("ix_daily_date_status", "report_date", "status"),
    )
    sa.Table(
        "daily_report_items", metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("daily_report_id", sa.Integer(), sa.ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_story_id", sa.Integer(), sa.ForeignKey("user_stories.id"), index=True),
        sa.Column("task_title", sa.String(255), nullable=False),
        sa.Column("yesterday_work", sa.Text()),
        sa.Column("today_plan", sa.Text()),
        sa.Column("issue_description", sa.Text()),
        sa.Column("has_issue", sa.Boolean(), nullable=False, index=True),
        sa.Column("progress_percent", sa.Integer()),
        *timestamps(),
    )
    sa.Table(
        "weekly_reports", metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("generated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot_data", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("GENERATED", "FINALIZED", name="weeklystatus"), nullable=False, index=True),
        sa.Index("ix_weekly_range", "week_start", "week_end"),
    )
    sa.Table(
        "settings", metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("setting_key", sa.String(100), nullable=False, unique=True),
        sa.Column("setting_value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
    )
    return metadata


def upgrade():
    # checkfirst also permits retry after SQLite persisted some initial DDL.
    initial_schema().create_all(bind=op.get_bind())


def downgrade():
    initial_schema().drop_all(bind=op.get_bind())

import enum
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utcnow

class Role(str, enum.Enum): ADMIN="ADMIN"; MEMBER="MEMBER"
class StoryStatus(str, enum.Enum): TODO="TODO"; IN_PROGRESS="IN_PROGRESS"; BLOCKED="BLOCKED"; DONE="DONE"; CLOSED="CLOSED"
class Priority(str, enum.Enum): LOW="LOW"; MEDIUM="MEDIUM"; HIGH="HIGH"; CRITICAL="CRITICAL"
class DailyStatus(str, enum.Enum): DRAFT="DRAFT"; SUBMITTED="SUBMITTED"
class WeeklyStatus(str, enum.Enum): GENERATED="GENERATED"; FINALIZED="FINALIZED"

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class User(TimestampMixin, Base):
    __tablename__="users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.MEMBER, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    assignments: Mapped[list["UserStoryAssignment"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class UserStory(TimestampMixin, Base):
    __tablename__="user_stories"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[StoryStatus] = mapped_column(Enum(StoryStatus), default=StoryStatus.TODO, index=True)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.MEDIUM, index=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    assignments: Mapped[list["UserStoryAssignment"]] = relationship(back_populates="story", cascade="all, delete-orphan")

class UserStoryAssignment(Base):
    __tablename__="user_story_assignments"
    __table_args__=(UniqueConstraint("user_story_id","user_id", name="uq_story_user"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_story_id: Mapped[int] = mapped_column(ForeignKey("user_stories.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    story: Mapped[UserStory] = relationship(back_populates="assignments")
    user: Mapped[User] = relationship(back_populates="assignments")

class DailyReport(TimestampMixin, Base):
    __tablename__="daily_reports"
    __table_args__=(UniqueConstraint("user_id","report_date",name="uq_daily_user_date"), Index("ix_daily_date_status","report_date","status"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    general_note: Mapped[Optional[str]] = mapped_column(Text)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[DailyStatus] = mapped_column(Enum(DailyStatus), default=DailyStatus.DRAFT, index=True)
    is_reopened: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user: Mapped[User] = relationship()
    items: Mapped[list["DailyReportItem"]] = relationship(back_populates="report", cascade="all, delete-orphan", order_by="DailyReportItem.id")
    reopen_history: Mapped[list["DailyReportReopenAudit"]] = relationship(back_populates="report", cascade="all, delete-orphan", order_by="DailyReportReopenAudit.reopened_at.desc()")

class DailyReportReopenAudit(Base):
    __tablename__="daily_report_reopen_audits"
    id: Mapped[int] = mapped_column(primary_key=True)
    daily_report_id: Mapped[int] = mapped_column(ForeignKey("daily_reports.id", ondelete="CASCADE"), index=True)
    reopened_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    reopened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    report: Mapped[DailyReport] = relationship(back_populates="reopen_history")
    admin: Mapped[User] = relationship()

class DailyReportItem(TimestampMixin, Base):
    __tablename__="daily_report_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    daily_report_id: Mapped[int] = mapped_column(ForeignKey("daily_reports.id", ondelete="CASCADE"), index=True)
    user_story_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user_stories.id"), index=True)
    task_title: Mapped[str] = mapped_column(String(255))
    yesterday_work: Mapped[Optional[str]] = mapped_column(Text)
    today_plan: Mapped[Optional[str]] = mapped_column(Text)
    issue_description: Mapped[Optional[str]] = mapped_column(Text)
    has_issue: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    progress_percent: Mapped[Optional[int]] = mapped_column(Integer)
    report: Mapped[DailyReport] = relationship(back_populates="items")
    user_story: Mapped[Optional[UserStory]] = relationship()

class WeeklyReport(Base):
    __tablename__="weekly_reports"
    __table_args__=(Index("ix_weekly_range","week_start","week_end"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(Date)
    week_end: Mapped[date] = mapped_column(Date)
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    snapshot_data: Mapped[str] = mapped_column(Text)
    status: Mapped[WeeklyStatus] = mapped_column(Enum(WeeklyStatus), default=WeeklyStatus.GENERATED, index=True)

class Setting(Base):
    __tablename__="settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    setting_key: Mapped[str] = mapped_column(String(100), unique=True)
    setting_value: Mapped[str] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)

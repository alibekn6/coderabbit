"""
SQLAlchemy models for caching Notion data.
These models store fetched Notion data to avoid repeated slow API calls.
"""
from src.db.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    DateTime,
    Integer,
    Boolean,
    Text,
    func
)
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime


class CacheMetadata(Base):
    """Tracks cache update status and timing for different Notion data types"""
    __tablename__ = "cache_metadata"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cache_type: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_update_scheduled: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_updating: Mapped[bool] = mapped_column(Boolean, default=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    update_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CachedNotionProject(Base):
    """Cached project data from Notion"""
    __tablename__ = "cached_notion_projects"

    page_id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    health_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    health_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    priority_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assignees: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    task_count: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    notion_created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notion_last_edited_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CachedNotionTask(Base):
    """Cached task data from Notion"""
    __tablename__ = "cached_notion_tasks"

    page_id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    task_name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    effort_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    task_type: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    assignee: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    notion_created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notion_last_edited_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CachedTeamMember(Base):
    """Cached team member information from Notion"""
    __tablename__ = "cached_team_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tg_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CachedNotionTodo(Base):
    """Cached todo/task data from team member Kanban boards"""
    __tablename__ = "cached_notion_todos"

    todo_id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    member_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    task_name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    deadline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_done: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    project_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    cached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

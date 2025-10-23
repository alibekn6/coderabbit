"""
Person and Activity tracking schemas for database models.

This module contains SQLAlchemy models for tracking persons and their activities
from Notion databases (conversations and tasks).
"""

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    DateTime,
    Integer,
    func,
    ForeignKey,
    Index,
    UniqueConstraint,
    Text,
    JSON
)
from src.db.database import Base


class Person(Base):
    """
    Person model representing a team member.

    Links to Notion users and tracks their activities across multiple databases.
    """
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    notion_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    telegram_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    conversation_activities: Mapped[list["ConversationActivity"]] = relationship(
        "ConversationActivity", back_populates="person", cascade="all, delete-orphan"
    )
    task_activities: Mapped[list["TaskActivity"]] = relationship(
        "TaskActivity", back_populates="person", cascade="all, delete-orphan"
    )
    activity_summaries: Mapped[list["ActivitySummary"]] = relationship(
        "ActivitySummary", back_populates="person", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Person(id={self.id}, username='{self.username}', notion_id='{self.notion_id}')>"


class ConversationActivity(Base):
    """
    Track voice conversations with attendees from Notion conversation_db.

    Each record represents one person's participation in a conversation.
    Multiple records can exist for the same conversation (one per attendee).
    """
    __tablename__ = "conversation_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    notion_conversation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    conversation_title: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    notion_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationship
    person: Mapped["Person"] = relationship("Person", back_populates="conversation_activities")

    # Composite index for efficient queries by person and date range
    # Also ensures one record per person per conversation
    __table_args__ = (
        Index("ix_conversation_person_created", "person_id", "created_at"),
        Index("ix_conversation_notion_id_person", "notion_conversation_id", "person_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ConversationActivity(id={self.id}, person_id={self.person_id}, title='{self.conversation_title}')>"


class TaskActivity(Base):
    """
    Track task completions by persons from Notion Kanban database.

    Records when a task status changes to "Done" by a person.
    """
    __tablename__ = "task_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    notion_task_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    task_title: Mapped[str] = mapped_column(String(500), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_status_change: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    notion_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationship
    person: Mapped["Person"] = relationship("Person", back_populates="task_activities")

    # Composite index for efficient queries by person and date range
    __table_args__ = (
        Index("ix_task_person_completed", "person_id", "completed_at"),
    )

    def __repr__(self) -> str:
        return f"<TaskActivity(id={self.id}, person_id={self.person_id}, task_title='{self.task_title}')>"


class ActivitySummary(Base):
    """
    Aggregated activity statistics per person per day.

    GitHub-style contribution tracking with daily rollups.
    Optimized for fast queries and leaderboard generation.
    """
    __tablename__ = "activity_summaries"

    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("persons.id", ondelete="CASCADE"), primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    conversations_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_activity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    person: Mapped["Person"] = relationship("Person", back_populates="activity_summaries")

    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_activity_date", "date"),
        Index("ix_activity_score", "total_activity_score"),
    )

    def __repr__(self) -> str:
        return f"<ActivitySummary(person_id={self.person_id}, date={self.date}, score={self.total_activity_score})>"

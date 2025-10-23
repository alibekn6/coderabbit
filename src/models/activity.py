"""
Pydantic models for Activity API requests and responses.
"""

from datetime import datetime, date
from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class ActivityType(str, Enum):
    """Types of activities."""
    CONVERSATION = "conversation"
    TASK = "task"
    ALL = "all"


class PeriodType(str, Enum):
    """Time period types for statistics."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ALL_TIME = "all_time"


# Conversation Activity Models

class ConversationActivityBase(BaseModel):
    """Base model for conversation activity."""
    notion_conversation_id: str = Field(..., max_length=100)
    conversation_title: Optional[str] = Field(None, max_length=500)
    created_at: datetime
    metadata: Optional[dict] = None


class ConversationActivityCreate(ConversationActivityBase):
    """Model for creating a conversation activity."""
    person_id: int


class ConversationActivityResponse(ConversationActivityBase):
    """Response model for conversation activity."""
    id: int
    person_id: int
    last_synced_at: datetime

    class Config:
        from_attributes = True


# Task Activity Models

class TaskActivityBase(BaseModel):
    """Base model for task activity."""
    notion_task_id: str = Field(..., max_length=100)
    task_title: Optional[str] = Field(None, max_length=500)
    project_name: Optional[str] = Field(None, max_length=255)
    completed_at: datetime
    last_status_change: Optional[datetime] = None
    metadata: Optional[dict] = None


class TaskActivityCreate(TaskActivityBase):
    """Model for creating a task activity."""
    person_id: int


class TaskActivityResponse(TaskActivityBase):
    """Response model for task activity."""
    id: int
    person_id: int
    last_synced_at: datetime

    class Config:
        from_attributes = True


# Combined Activity Response

class ActivityItem(BaseModel):
    """Combined activity item for timeline."""
    id: int
    activity_type: ActivityType
    title: str
    occurred_at: datetime
    person_id: int
    metadata: Optional[dict] = None


class ActivityTimelineResponse(BaseModel):
    """Response model for activity timeline."""
    total: int
    activities: list[ActivityItem]
    has_more: bool = False


# Activity Statistics Models

class DailyActivityStats(BaseModel):
    """Daily activity statistics."""
    date: date
    conversations_created: int = 0
    tasks_completed: int = 0
    total_activity_score: int = 0


class ActivityStatsResponse(BaseModel):
    """Response model for activity statistics."""
    person_id: int
    period: PeriodType
    start_date: date
    end_date: date
    total_conversations: int = 0
    total_tasks_completed: int = 0
    total_activity_score: int = 0
    daily_breakdown: list[DailyActivityStats] = []


class HeatmapData(BaseModel):
    """GitHub-style heatmap data point."""
    date: date
    count: int
    level: int = Field(..., ge=0, le=4, description="Activity level 0-4")


class HeatmapResponse(BaseModel):
    """Response model for activity heatmap."""
    person_id: int
    start_date: date
    end_date: date
    total_days: int
    active_days: int
    max_activity: int
    data: list[HeatmapData]


class LeaderboardEntry(BaseModel):
    """Leaderboard entry."""
    rank: int
    person_id: int
    username: str
    conversations_created: int = 0
    tasks_completed: int = 0
    total_activity_score: int = 0


class LeaderboardResponse(BaseModel):
    """Response model for leaderboard."""
    period: PeriodType
    start_date: date
    end_date: date
    entries: list[LeaderboardEntry]


class StreakInfo(BaseModel):
    """Streak information for a person."""
    person_id: int
    current_streak: int = 0
    longest_streak: int = 0
    current_streak_start: Optional[date] = None
    longest_streak_start: Optional[date] = None
    longest_streak_end: Optional[date] = None


class ActivitySyncResponse(BaseModel):
    """Response model for activity sync operation."""
    success: bool
    conversations_synced: int = 0
    tasks_synced: int = 0
    persons_created: int = 0
    persons_updated: int = 0
    errors: list[str] = []
    sync_duration_seconds: float

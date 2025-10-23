"""
Pydantic models for Person API requests and responses.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional


class PersonBase(BaseModel):
    """Base Person model with common fields."""
    notion_id: str = Field(..., min_length=1, max_length=100, description="Notion user ID")
    username: str = Field(..., min_length=1, max_length=255, description="Username")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar URL")
    email: Optional[EmailStr] = Field(None, description="Email address")
    telegram_id: Optional[str] = Field(None, max_length=100, description="Telegram user ID")


class PersonCreate(PersonBase):
    """Model for creating a new Person."""
    pass


class PersonUpdate(BaseModel):
    """Model for updating a Person."""
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None
    telegram_id: Optional[str] = Field(None, max_length=100)


class PersonResponse(PersonBase):
    """Model for Person API response."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PersonWithStats(PersonResponse):
    """Person response with activity statistics."""
    total_conversations: int = Field(default=0, description="Total conversations created")
    total_tasks_completed: int = Field(default=0, description="Total tasks completed")
    total_activity_score: int = Field(default=0, description="Total activity score")
    current_streak: int = Field(default=0, description="Current consecutive days with activity")
    longest_streak: int = Field(default=0, description="Longest streak of consecutive days")


class PersonListResponse(BaseModel):
    """Response model for listing persons."""
    total: int
    persons: list[PersonResponse]


class PersonStatsListResponse(BaseModel):
    """Response model for listing persons with stats."""
    total: int
    persons: list[PersonWithStats]

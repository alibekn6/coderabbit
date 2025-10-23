"""
Activity repository for database operations.

This repository handles CRUD operations for activity tracking entities.
"""

from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict
from sqlalchemy import select, func, and_, or_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.person import (
    ConversationActivity,
    TaskActivity,
    ActivitySummary,
    Person
)
from src.core.logging import get_logger

logger = get_logger(__name__)


class ActivityRepository:
    """Repository for Activity-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== Conversation Activity ====================

    async def create_conversation_activity(
        self,
        person_id: int,
        notion_conversation_id: str,
        conversation_title: Optional[str],
        created_at: datetime,
        notion_metadata: Optional[dict] = None
    ) -> ConversationActivity:
        """Create a new conversation activity."""
        activity = ConversationActivity(
            person_id=person_id,
            notion_conversation_id=notion_conversation_id,
            conversation_title=conversation_title,
            created_at=created_at,
            notion_metadata=notion_metadata
        )

        self.session.add(activity)
        await self.session.flush()
        await self.session.refresh(activity)

        logger.info(
            "conversation_activity_created",
            activity_id=activity.id,
            person_id=person_id,
            notion_conversation_id=notion_conversation_id
        )
        return activity

    async def get_conversation_by_notion_id(
        self, notion_conversation_id: str
    ) -> Optional[ConversationActivity]:
        """Get conversation activity by Notion ID (returns first match)."""
        result = await self.session.execute(
            select(ConversationActivity).where(
                ConversationActivity.notion_conversation_id == notion_conversation_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_conversation_by_notion_id_and_person(
        self, notion_conversation_id: str, person_id: int
    ) -> Optional[ConversationActivity]:
        """Get conversation activity by Notion ID and person ID."""
        result = await self.session.execute(
            select(ConversationActivity).where(
                ConversationActivity.notion_conversation_id == notion_conversation_id,
                ConversationActivity.person_id == person_id
            )
        )
        return result.scalar_one_or_none()

    async def bulk_create_conversations(
        self, conversations: List[dict]
    ) -> List[ConversationActivity]:
        """Bulk create conversation activities (idempotent).
        
        Creates one activity per attendee per conversation.
        Uses composite unique constraint (notion_conversation_id, person_id).
        """
        created = []
        updated = []
        
        for conv in conversations:
            existing = await self.get_conversation_by_notion_id_and_person(
                conv["notion_conversation_id"],
                conv["person_id"]
            )
            if not existing:
                activity = await self.create_conversation_activity(**conv)
                created.append(activity)
            else:
                # Update fields if changed or missing
                updated_fields = False
                
                if conv.get("conversation_title") and existing.conversation_title != conv["conversation_title"]:
                    existing.conversation_title = conv["conversation_title"]
                    updated_fields = True
                
                if conv.get("notion_metadata") and not existing.notion_metadata:
                    existing.notion_metadata = conv["notion_metadata"]
                    updated_fields = True
                
                if conv.get("created_at") and existing.created_at != conv["created_at"]:
                    existing.created_at = conv["created_at"]
                    updated_fields = True
                
                # Always update last_synced_at
                existing.last_synced_at = datetime.utcnow()
                
                if updated_fields:
                    updated.append(existing)
                
                await self.session.flush()

        logger.info("bulk_conversations_created", count=len(created), updated=len(updated))
        return created

    # ==================== Task Activity ====================

    async def create_task_activity(
        self,
        person_id: int,
        notion_task_id: str,
        task_title: Optional[str],
        project_name: Optional[str],
        completed_at: datetime,
        last_status_change: Optional[datetime] = None,
        notion_metadata: Optional[dict] = None
    ) -> TaskActivity:
        """Create a new task activity."""
        activity = TaskActivity(
            person_id=person_id,
            notion_task_id=notion_task_id,
            task_title=task_title,
            project_name=project_name,
            completed_at=completed_at,
            last_status_change=last_status_change,
            notion_metadata=notion_metadata
        )

        self.session.add(activity)
        await self.session.flush()
        await self.session.refresh(activity)

        logger.info(
            "task_activity_created",
            activity_id=activity.id,
            person_id=person_id,
            notion_task_id=notion_task_id
        )
        return activity

    async def get_task_by_notion_id(self, notion_task_id: str) -> Optional[TaskActivity]:
        """Get task activity by Notion ID."""
        result = await self.session.execute(
            select(TaskActivity).where(TaskActivity.notion_task_id == notion_task_id)
        )
        return result.scalar_one_or_none()

    async def bulk_create_tasks(self, tasks: List[dict]) -> List[TaskActivity]:
        """Bulk create task activities (idempotent)."""
        created = []
        updated = []
        
        for task in tasks:
            existing = await self.get_task_by_notion_id(task["notion_task_id"])
            if not existing:
                activity = await self.create_task_activity(**task)
                created.append(activity)
            else:
                # Update fields if changed or missing
                updated_fields = False
                
                if task.get("task_title") and existing.task_title != task["task_title"]:
                    existing.task_title = task["task_title"]
                    updated_fields = True
                
                if task.get("project_name") != existing.project_name:
                    existing.project_name = task.get("project_name")
                    updated_fields = True
                
                if task.get("notion_metadata") and not existing.notion_metadata:
                    existing.notion_metadata = task["notion_metadata"]
                    updated_fields = True
                
                if task.get("completed_at") and existing.completed_at != task["completed_at"]:
                    existing.completed_at = task["completed_at"]
                    updated_fields = True
                
                if task.get("last_status_change") and existing.last_status_change != task["last_status_change"]:
                    existing.last_status_change = task["last_status_change"]
                    updated_fields = True
                
                # Always update last_synced_at
                existing.last_synced_at = datetime.utcnow()
                
                if updated_fields:
                    updated.append(existing)
                
                await self.session.flush()

        logger.info("bulk_tasks_created", count=len(created), updated=len(updated))
        return created

    # ==================== Activity Queries ====================

    async def get_person_activities(
        self,
        person_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        activity_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[dict], int]:
        """
        Get all activities for a person with filtering and pagination.

        Returns a combined list of conversations and tasks sorted by time.
        """
        activities = []

        # Fetch conversations
        if not activity_type or activity_type in ("conversation", "all"):
            conv_query = select(ConversationActivity).where(
                ConversationActivity.person_id == person_id
            )
            if start_date:
                conv_query = conv_query.where(ConversationActivity.created_at >= start_date)
            if end_date:
                conv_query = conv_query.where(ConversationActivity.created_at <= end_date)

            conv_result = await self.session.execute(conv_query)
            conversations = conv_result.scalars().all()

            for conv in conversations:
                activities.append({
                    "id": conv.id,
                    "activity_type": "conversation",
                    "title": conv.conversation_title or "Untitled Conversation",
                    "occurred_at": conv.created_at,
                    "person_id": conv.person_id,
                    "metadata": conv.metadata
                })

        # Fetch tasks
        if not activity_type or activity_type in ("task", "all"):
            task_query = select(TaskActivity).where(TaskActivity.person_id == person_id)
            if start_date:
                task_query = task_query.where(TaskActivity.completed_at >= start_date)
            if end_date:
                task_query = task_query.where(TaskActivity.completed_at <= end_date)

            task_result = await self.session.execute(task_query)
            tasks = task_result.scalars().all()

            for task in tasks:
                activities.append({
                    "id": task.id,
                    "activity_type": "task",
                    "title": task.task_title or "Untitled Task",
                    "occurred_at": task.completed_at,
                    "person_id": task.person_id,
                    "metadata": task.metadata
                })

        # Sort by time (most recent first)
        activities.sort(key=lambda x: x["occurred_at"], reverse=True)

        total = len(activities)
        paginated = activities[skip : skip + limit]

        return paginated, total

    # ==================== Activity Summary ====================

    async def create_or_update_summary(
        self,
        person_id: int,
        date: datetime,
        conversations_created: int = 0,
        tasks_completed: int = 0,
        total_activity_score: int = 0
    ) -> ActivitySummary:
        """Create or update daily activity summary."""
        # Try to get existing summary using date-only comparison to handle timezone differences
        result = await self.session.execute(
            select(ActivitySummary).where(
                and_(
                    ActivitySummary.person_id == person_id,
                    func.date(ActivitySummary.date) == date.date()
                )
            )
        )
        summary = result.scalar_one_or_none()

        if summary:
            # Update existing (also update the date to ensure it's timezone-aware)
            summary.date = date
            summary.conversations_created = conversations_created
            summary.tasks_completed = tasks_completed
            summary.total_activity_score = total_activity_score
        else:
            # Create new
            summary = ActivitySummary(
                person_id=person_id,
                date=date,
                conversations_created=conversations_created,
                tasks_completed=tasks_completed,
                total_activity_score=total_activity_score
            )
            self.session.add(summary)

        await self.session.flush()
        await self.session.refresh(summary)

        return summary

    async def get_summaries_for_person(
        self,
        person_id: int,
        start_date: date,
        end_date: date
    ) -> List[ActivitySummary]:
        """Get activity summaries for a person within a date range."""
        result = await self.session.execute(
            select(ActivitySummary)
            .where(
                and_(
                    ActivitySummary.person_id == person_id,
                    ActivitySummary.date >= start_date,
                    ActivitySummary.date <= end_date
                )
            )
            .order_by(ActivitySummary.date)
        )
        return list(result.scalars().all())

    async def aggregate_daily_activities(
        self, person_id: int, target_date: date
    ) -> ActivitySummary:
        """
        Aggregate activities for a person on a specific date.

        Calculates counts from conversation and task activities.
        """
        # Use UTC timezone-aware datetimes to match database timestamps (from Notion sync)
        start_datetime = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Count conversations
        conv_result = await self.session.execute(
            select(func.count(ConversationActivity.id)).where(
                and_(
                    ConversationActivity.person_id == person_id,
                    ConversationActivity.created_at >= start_datetime,
                    ConversationActivity.created_at <= end_datetime
                )
            )
        )
        conversations_count = conv_result.scalar_one()

        # Count tasks
        task_result = await self.session.execute(
            select(func.count(TaskActivity.id)).where(
                and_(
                    TaskActivity.person_id == person_id,
                    TaskActivity.completed_at >= start_datetime,
                    TaskActivity.completed_at <= end_datetime
                )
            )
        )
        tasks_count = task_result.scalar_one()

        # Calculate activity score (conversations worth 1 point, tasks worth 2 points)
        total_score = conversations_count + (tasks_count * 2)

        # Create or update summary
        summary = await self.create_or_update_summary(
            person_id=person_id,
            date=start_datetime,
            conversations_created=conversations_count,
            tasks_completed=tasks_count,
            total_activity_score=total_score
        )

        return summary

    async def get_leaderboard(
        self,
        start_date: date,
        end_date: date,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get leaderboard for a date range.

        Returns top performers sorted by total activity score.
        """
        result = await self.session.execute(
            select(
                Person.id,
                Person.username,
                func.sum(ActivitySummary.conversations_created).label("total_conversations"),
                func.sum(ActivitySummary.tasks_completed).label("total_tasks"),
                func.sum(ActivitySummary.total_activity_score).label("total_score")
            )
            .join(Person, ActivitySummary.person_id == Person.id)
            .where(
                and_(
                    ActivitySummary.date >= start_date,
                    ActivitySummary.date <= end_date
                )
            )
            .group_by(Person.id, Person.username)
            .order_by(desc("total_score"))
            .limit(limit)
        )

        rows = result.all()
        leaderboard = []
        for rank, row in enumerate(rows, start=1):
            leaderboard.append({
                "rank": rank,
                "person_id": row.id,
                "username": row.username,
                "conversations_created": int(row.total_conversations or 0),
                "tasks_completed": int(row.total_tasks or 0),
                "total_activity_score": int(row.total_score or 0)
            })

        return leaderboard

    async def calculate_streak(self, person_id: int) -> Dict:
        """
        Calculate current and longest streak for a person.

        A streak is consecutive days with activity.
        """
        # Get all activity dates
        result = await self.session.execute(
            select(ActivitySummary.date)
            .where(
                and_(
                    ActivitySummary.person_id == person_id,
                    ActivitySummary.total_activity_score > 0
                )
            )
            .order_by(ActivitySummary.date)
        )
        activity_dates = [row[0].date() if isinstance(row[0], datetime) else row[0] for row in result.all()]

        if not activity_dates:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "current_streak_start": None,
                "longest_streak_start": None,
                "longest_streak_end": None
            }

        # Calculate streaks
        current_streak = 0
        current_streak_start = None
        longest_streak = 0
        longest_streak_start = None
        longest_streak_end = None
        temp_streak = 1
        temp_streak_start = activity_dates[0]

        today = date.today()

        for i in range(1, len(activity_dates)):
            prev_date = activity_dates[i - 1]
            curr_date = activity_dates[i]

            if (curr_date - prev_date).days == 1:
                temp_streak += 1
            else:
                # Streak broken
                if temp_streak > longest_streak:
                    longest_streak = temp_streak
                    longest_streak_start = temp_streak_start
                    longest_streak_end = prev_date

                temp_streak = 1
                temp_streak_start = curr_date

        # Check final streak
        if temp_streak > longest_streak:
            longest_streak = temp_streak
            longest_streak_start = temp_streak_start
            longest_streak_end = activity_dates[-1]

        # Calculate current streak (must include today or yesterday)
        last_activity = activity_dates[-1]
        days_since_last = (today - last_activity).days

        if days_since_last <= 1:
            # Current streak is active
            current_streak = 1
            current_streak_start = last_activity

            # Count backwards
            for i in range(len(activity_dates) - 2, -1, -1):
                if (activity_dates[i + 1] - activity_dates[i]).days == 1:
                    current_streak += 1
                    current_streak_start = activity_dates[i]
                else:
                    break
        else:
            current_streak = 0
            current_streak_start = None

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "current_streak_start": current_streak_start,
            "longest_streak_start": longest_streak_start,
            "longest_streak_end": longest_streak_end
        }

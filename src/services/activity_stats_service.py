"""
Activity statistics service.

This service handles activity statistics calculations and aggregations.
"""

from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.activity_repository import ActivityRepository
from src.models.activity import (
    ActivityTimelineResponse,
    ActivityItem,
    ActivityType,
    PeriodType,
    ActivityStatsResponse,
    DailyActivityStats,
    HeatmapResponse,
    HeatmapData,
    LeaderboardResponse,
    LeaderboardEntry,
    StreakInfo
)
from src.core.logging import get_logger

logger = get_logger(__name__)


class ActivityStatsService:
    """Service for activity statistics and aggregations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.activity_repo = ActivityRepository(session)

    async def get_person_timeline(
        self,
        person_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        activity_type: Optional[ActivityType] = None,
        skip: int = 0,
        limit: int = 100
    ) -> ActivityTimelineResponse:
        """
        Get activity timeline for a person.

        Args:
            person_id: Person ID
            start_date: Start date filter
            end_date: End date filter
            activity_type: Filter by activity type
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Activity timeline response
        """
        type_filter = activity_type.value if activity_type else None

        activities, total = await self.activity_repo.get_person_activities(
            person_id=person_id,
            start_date=start_date,
            end_date=end_date,
            activity_type=type_filter,
            skip=skip,
            limit=limit
        )

        activity_items = [ActivityItem(**activity) for activity in activities]

        return ActivityTimelineResponse(
            total=total,
            activities=activity_items,
            has_more=(skip + limit) < total
        )

    async def get_person_stats(
        self,
        person_id: int,
        period: PeriodType = PeriodType.MONTHLY,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> ActivityStatsResponse:
        """
        Get aggregated activity statistics for a person.

        Args:
            person_id: Person ID
            period: Time period type
            start_date: Custom start date (optional)
            end_date: Custom end date (optional)

        Returns:
            Activity statistics response
        """
        # Calculate date range based on period
        if not start_date or not end_date:
            start_date, end_date = self._calculate_period_range(period)

        # Get summaries for the period
        summaries = await self.activity_repo.get_summaries_for_person(
            person_id=person_id, start_date=start_date, end_date=end_date
        )

        # Aggregate totals
        total_conversations = sum(s.conversations_created for s in summaries)
        total_tasks = sum(s.tasks_completed for s in summaries)
        total_score = sum(s.total_activity_score for s in summaries)

        # Create daily breakdown
        daily_breakdown = [
            DailyActivityStats(
                date=s.date.date() if isinstance(s.date, datetime) else s.date,
                conversations_created=s.conversations_created,
                tasks_completed=s.tasks_completed,
                total_activity_score=s.total_activity_score
            )
            for s in summaries
        ]

        return ActivityStatsResponse(
            person_id=person_id,
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_conversations=total_conversations,
            total_tasks_completed=total_tasks,
            total_activity_score=total_score,
            daily_breakdown=daily_breakdown
        )

    async def get_heatmap(
        self, person_id: int, days: int = 365
    ) -> HeatmapResponse:
        """
        Get GitHub-style activity heatmap data.

        Args:
            person_id: Person ID
            days: Number of days to include (default 365)

        Returns:
            Heatmap response
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Get summaries
        summaries = await self.activity_repo.get_summaries_for_person(
            person_id=person_id, start_date=start_date, end_date=end_date
        )

        # Create a map of date -> activity score
        activity_map = {
            (s.date.date() if isinstance(s.date, datetime) else s.date): s.total_activity_score
            for s in summaries
        }

        # Calculate max activity for level calculation
        max_activity = max(activity_map.values()) if activity_map else 1

        # Generate heatmap data for all days in range
        heatmap_data = []
        current_date = start_date
        active_days = 0

        while current_date <= end_date:
            activity_count = activity_map.get(current_date, 0)
            if activity_count > 0:
                active_days += 1

            # Calculate level (0-4 like GitHub)
            if activity_count == 0:
                level = 0
            elif activity_count >= max_activity * 0.75:
                level = 4
            elif activity_count >= max_activity * 0.5:
                level = 3
            elif activity_count >= max_activity * 0.25:
                level = 2
            else:
                level = 1

            heatmap_data.append(
                HeatmapData(date=current_date, count=activity_count, level=level)
            )

            current_date += timedelta(days=1)

        return HeatmapResponse(
            person_id=person_id,
            start_date=start_date,
            end_date=end_date,
            total_days=days,
            active_days=active_days,
            max_activity=max_activity,
            data=heatmap_data
        )

    async def get_leaderboard(
        self, period: PeriodType = PeriodType.MONTHLY, limit: int = 10
    ) -> LeaderboardResponse:
        """
        Get activity leaderboard.

        Args:
            period: Time period type
            limit: Number of entries to return

        Returns:
            Leaderboard response
        """
        start_date, end_date = self._calculate_period_range(period)

        leaderboard_data = await self.activity_repo.get_leaderboard(
            start_date=start_date, end_date=end_date, limit=limit
        )

        entries = [LeaderboardEntry(**entry) for entry in leaderboard_data]

        return LeaderboardResponse(
            period=period, start_date=start_date, end_date=end_date, entries=entries
        )

    async def get_streak_info(self, person_id: int) -> StreakInfo:
        """
        Get streak information for a person.

        Args:
            person_id: Person ID

        Returns:
            Streak information
        """
        streak_data = await self.activity_repo.calculate_streak(person_id)

        return StreakInfo(person_id=person_id, **streak_data)

    async def aggregate_daily_activities(
        self, person_id: int, target_date: date
    ) -> DailyActivityStats:
        """
        Aggregate activities for a person on a specific date.

        Args:
            person_id: Person ID
            target_date: Date to aggregate

        Returns:
            Daily activity statistics
        """
        summary = await self.activity_repo.aggregate_daily_activities(
            person_id=person_id, target_date=target_date
        )

        return DailyActivityStats(
            date=target_date,
            conversations_created=summary.conversations_created,
            tasks_completed=summary.tasks_completed,
            total_activity_score=summary.total_activity_score
        )

    async def bulk_aggregate_daily_activities(
        self, start_date: date, end_date: date
    ) -> int:
        """
        Aggregate daily activities for all persons in a date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Number of summaries created/updated
        """
        from src.repositories.person_repository import PersonRepository

        person_repo = PersonRepository(self.session)
        persons, _ = await person_repo.get_all(limit=10000)  # Get all persons

        count = 0
        current_date = start_date

        while current_date <= end_date:
            for person in persons:
                try:
                    await self.activity_repo.aggregate_daily_activities(
                        person_id=person.id, target_date=current_date
                    )
                    count += 1
                except Exception as e:
                    logger.error(
                        "aggregation_failed",
                        person_id=person.id,
                        date=current_date,
                        error=str(e)
                    )

            current_date += timedelta(days=1)

        await self.session.commit()
        logger.info("bulk_aggregation_completed", summaries_created=count)

        return count

    def _calculate_period_range(self, period: PeriodType) -> tuple[date, date]:
        """Calculate start and end dates for a period type."""
        today = date.today()

        if period == PeriodType.DAILY:
            return today, today

        elif period == PeriodType.WEEKLY:
            start = today - timedelta(days=today.weekday())  # Monday
            return start, today

        elif period == PeriodType.MONTHLY:
            start = today.replace(day=1)
            return start, today

        elif period == PeriodType.YEARLY:
            start = today.replace(month=1, day=1)
            return start, today

        else:  # ALL_TIME
            # Return a very early date
            return date(2020, 1, 1), today

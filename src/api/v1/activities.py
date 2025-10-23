"""
Activity API endpoints.

This module contains API routes for activity tracking and statistics.
"""

import calendar
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.services.activity_sync_service import ActivitySyncService
from src.services.activity_stats_service import ActivityStatsService
from src.models.activity import (
    ActivityTimelineResponse,
    ActivityType,
    PeriodType,
    ActivityStatsResponse,
    HeatmapResponse,
    LeaderboardResponse,
    StreakInfo,
    ActivitySyncResponse
)
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/activities/person/{person_id}", response_model=ActivityTimelineResponse)
async def get_person_timeline(
    person_id: int,
    start_date: datetime = Query(None, description="Start date filter"),
    end_date: datetime = Query(None, description="End date filter"),
    activity_type: ActivityType = Query(None, description="Filter by activity type"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Pagination limit"),
    db: AsyncSession = Depends(get_db)
) -> ActivityTimelineResponse:
    """
    Get activity timeline for a person.

    Returns a combined list of conversations and tasks sorted by time.

    Args:
        person_id: Person ID
        start_date: Start date filter
        end_date: End date filter
        activity_type: Filter by activity type
        skip: Pagination offset
        limit: Pagination limit
        db: Database session

    Returns:
        Activity timeline
    """
    logger.info(
        "get_person_timeline_request",
        person_id=person_id,
        activity_type=activity_type,
        skip=skip,
        limit=limit
    )

    try:
        service = ActivityStatsService(db)
        timeline = await service.get_person_timeline(
            person_id=person_id,
            start_date=start_date,
            end_date=end_date,
            activity_type=activity_type,
            skip=skip,
            limit=limit
        )
        return timeline

    except Exception as e:
        logger.error("get_person_timeline_error", person_id=person_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/activities/person/{person_id}/stats", response_model=ActivityStatsResponse)
async def get_person_stats(
    person_id: int,
    period: PeriodType = Query(PeriodType.MONTHLY, description="Time period type"),
    start_date: date = Query(None, description="Custom start date"),
    end_date: date = Query(None, description="Custom end date"),
    db: AsyncSession = Depends(get_db)
) -> ActivityStatsResponse:
    """
    Get aggregated activity statistics for a person.

    Args:
        person_id: Person ID
        period: Time period type (daily, weekly, monthly, yearly, all_time)
        start_date: Custom start date (optional)
        end_date: Custom end date (optional)
        db: Database session

    Returns:
        Activity statistics with daily breakdown
    """
    logger.info(
        "get_person_stats_request",
        person_id=person_id,
        period=period,
        start_date=start_date,
        end_date=end_date
    )

    try:
        service = ActivityStatsService(db)
        stats = await service.get_person_stats(
            person_id=person_id,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
        return stats

    except Exception as e:
        logger.error("get_person_stats_error", person_id=person_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/activities/person/{person_id}/heatmap", response_model=HeatmapResponse)
async def get_person_heatmap(
    person_id: int,
    days: int = Query(365, ge=1, le=730, description="Number of days to include"),
    db: AsyncSession = Depends(get_db)
) -> HeatmapResponse:
    """
    Get GitHub-style activity heatmap data for a person.

    Args:
        person_id: Person ID
        days: Number of days to include (default 365)
        db: Database session

    Returns:
        Heatmap data with activity levels
    """
    logger.info("get_person_heatmap_request", person_id=person_id, days=days)

    try:
        service = ActivityStatsService(db)
        heatmap = await service.get_heatmap(person_id=person_id, days=days)
        return heatmap

    except Exception as e:
        logger.error("get_person_heatmap_error", person_id=person_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/activities/person/{person_id}/streak", response_model=StreakInfo)
async def get_person_streak(
    person_id: int, db: AsyncSession = Depends(get_db)
) -> StreakInfo:
    """
    Get streak information for a person.

    Returns current and longest streaks of consecutive days with activity.

    Args:
        person_id: Person ID
        db: Database session

    Returns:
        Streak information
    """
    logger.info("get_person_streak_request", person_id=person_id)

    try:
        service = ActivityStatsService(db)
        streak = await service.get_streak_info(person_id=person_id)
        return streak

    except Exception as e:
        logger.error("get_person_streak_error", person_id=person_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/activities/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: PeriodType = Query(PeriodType.MONTHLY, description="Time period type"),
    limit: int = Query(10, ge=1, le=100, description="Number of top entries"),
    db: AsyncSession = Depends(get_db)
) -> LeaderboardResponse:
    """
    Get activity leaderboard.

    Returns top performers sorted by total activity score.

    Args:
        period: Time period type (daily, weekly, monthly, yearly, all_time)
        limit: Number of entries to return
        db: Database session

    Returns:
        Leaderboard with rankings
    """
    logger.info("get_leaderboard_request", period=period, limit=limit)

    try:
        service = ActivityStatsService(db)
        leaderboard = await service.get_leaderboard(period=period, limit=limit)
        return leaderboard

    except Exception as e:
        logger.error("get_leaderboard_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/activities/aggregate-month")
async def aggregate_monthly_summaries(
    year: int = Query(None, description="Year (defaults to current year)"),
    month: int = Query(None, ge=1, le=12, description="Month (defaults to current month)"),
    background_tasks: BackgroundTasks = None,
    background: bool = Query(False, description="Run aggregation in background"),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate daily activity summaries for a specific month.
    
    Creates ActivitySummary records for every day in the specified month,
    including days with zero activity. This ensures heatmaps have complete data.
    
    Args:
        year: Year (defaults to current year)
        month: Month (defaults to current month)
        background: Run aggregation in background
        db: Database session
        
    Returns:
        Aggregation statistics
    """
    # Default to current month if not specified
    today = date.today()
    year = year or today.year
    month = month or today.month
    
    # Calculate date range for the month
    start_date = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = date(year, month, last_day)
    
    # Don't go beyond today
    if end_date > today:
        end_date = today
    
    logger.info(
        "aggregate_monthly_summaries_request",
        year=year,
        month=month,
        start_date=start_date,
        end_date=end_date,
        background=background
    )
    
    try:
        service = ActivityStatsService(db)
        
        if background and background_tasks:
            # Run in background
            background_tasks.add_task(
                service.bulk_aggregate_daily_activities,
                start_date=start_date,
                end_date=end_date
            )
            return {
                "status": "aggregation_started",
                "year": year,
                "month": month,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "message": "Aggregation started in background"
            }
        else:
            # Run synchronously
            count = await service.bulk_aggregate_daily_activities(
                start_date=start_date,
                end_date=end_date
            )
            
            return {
                "status": "completed",
                "year": year,
                "month": month,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "summaries_created": count
            }
    
    except Exception as e:
        logger.error("aggregate_monthly_summaries_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Aggregation failed: {str(e)}")


@router.post("/activities/sync", response_model=ActivitySyncResponse)
async def sync_activities(
    background_tasks: BackgroundTasks,
    incremental: bool = Query(True, description="Only sync recent changes"),
    background: bool = Query(False, description="Run sync in background"),
    db: AsyncSession = Depends(get_db)
) -> ActivitySyncResponse:
    """
    Sync activities from Notion databases.

    This endpoint triggers a sync operation to pull conversation and task activities
    from Notion databases. Database IDs are read from config (NOTION_CONVERSATION_DATABASE_ID, NOTION_KANBAN_DATABASE_ID).

    Args:
        background_tasks: FastAPI background tasks
        incremental: Only sync recent changes
        background: Run sync in background
        db: Database session

    Returns:
        Sync statistics
    """
    logger.info(
        "sync_activities_request",
        incremental=incremental,
        background=background
    )

    try:
        service = ActivitySyncService(db)

        if background:
            # Run sync in background
            background_tasks.add_task(
                service.sync_all,
                incremental=incremental
            )

            return ActivitySyncResponse(
                success=True,
                conversations_synced=0,
                tasks_synced=0,
                persons_created=0,
                persons_updated=0,
                errors=[],
                sync_duration_seconds=0.0
            )

        else:
            # Run sync synchronously
            result = await service.sync_all(
                incremental=incremental
            )

            return ActivitySyncResponse(
                success=len(result.get("errors", [])) == 0,
                **result
            )

    except Exception as e:
        logger.error("sync_activities_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/activities/aggregate", status_code=202)
async def aggregate_daily_activities(
    background_tasks: BackgroundTasks,
    start_date: date = Query(..., description="Start date for aggregation"),
    end_date: date = Query(None, description="End date for aggregation"),
    db: AsyncSession = Depends(get_db)
):
    """
    Aggregate daily activities for all persons.

    This is a maintenance endpoint that recalculates activity summaries
    for a given date range. Should be run periodically (e.g., daily cron job).

    Args:
        background_tasks: FastAPI background tasks
        start_date: Start date
        end_date: End date (defaults to today)
        db: Database session

    Returns:
        Accepted response (processing in background)
    """
    if not end_date:
        end_date = date.today()

    logger.info("aggregate_daily_activities_request", start_date=start_date, end_date=end_date)

    try:
        service = ActivityStatsService(db)

        # Run aggregation in background
        background_tasks.add_task(
            service.bulk_aggregate_daily_activities,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "message": "Aggregation started in background",
            "start_date": start_date,
            "end_date": end_date
        }

    except Exception as e:
        logger.error("aggregate_daily_activities_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

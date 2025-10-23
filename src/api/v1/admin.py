"""
Admin endpoints for system management and monitoring.
"""

from fastapi import APIRouter
from src.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/sync-activities")
async def trigger_activities_sync():
    """
    Manually trigger the activities sync task.

    This endpoint triggers the Celery task that:
    1. Syncs all conversations and completed tasks from Notion (full sync)
    2. Aggregates daily summaries for the entire year for each person

    Returns the task ID for tracking.

    Note: Requires Celery worker to be running.
    """
    from src.tasks.notion_cache_tasks import update_activities_cache

    try:
        # Trigger the task asynchronously via Celery
        result = update_activities_cache.delay()

        logger.info("activities_sync_triggered", task_id=result.id)

        return {
            "status": "success",
            "message": "Activities sync task triggered successfully",
            "task_id": result.id,
            "note": "Task is running in background. Check Celery logs for progress.",
            "check_status_url": f"/api/v1/admin/sync-activities/{result.id}"
        }
    except Exception as e:
        logger.error("failed_to_trigger_sync", error=str(e))
        return {
            "status": "error",
            "message": f"Failed to trigger sync task: {str(e)}",
            "note": "Make sure Celery worker and Redis are running"
        }


@router.get("/sync-activities/{task_id}")
async def check_sync_task_status(task_id: str):
    """
    Check the status of a sync task.

    Returns the current state and result of the task.

    Possible states:
    - PENDING: Task is waiting to be executed
    - STARTED: Task has been started
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed with an error
    - RETRY: Task is being retried

    Note: Requires Redis to be configured as Celery result backend.
    """
    from celery.result import AsyncResult
    from src.celery_app import celery_app

    try:
        task_result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "state": task_result.state,
        }

        if task_result.state == "PENDING":
            response["message"] = "Task is waiting to be executed or doesn't exist"
            response["info"] = None
        elif task_result.state == "STARTED":
            response["message"] = "Task is currently running"
            response["info"] = task_result.info
        elif task_result.state == "SUCCESS":
            response["message"] = "Task completed successfully"
            response["result"] = task_result.result
            response["info"] = {
                "conversations_synced": task_result.result.get("conversations_synced"),
                "tasks_synced": task_result.result.get("tasks_synced"),
                "persons_created": task_result.result.get("persons_created"),
                "persons_updated": task_result.result.get("persons_updated"),
                "summaries_created": task_result.result.get("summaries_created"),
                "duration_seconds": task_result.result.get("duration_seconds")
            }
        elif task_result.state == "FAILURE":
            response["message"] = "Task failed"
            response["error"] = str(task_result.info)
        elif task_result.state == "RETRY":
            response["message"] = "Task is being retried"
            response["info"] = str(task_result.info)
        else:
            response["message"] = f"Unknown state: {task_result.state}"
            response["info"] = str(task_result.info)

        return response

    except Exception as e:
        logger.error("failed_to_check_task_status", task_id=task_id, error=str(e))
        return {
            "status": "error",
            "message": f"Failed to check task status: {str(e)}",
            "note": "Make sure Redis is running and configured as Celery result backend"
        }


@router.get("/sync-activities-stats")
async def get_latest_sync_stats():
    """
    Get statistics from the latest activity sync.

    This endpoint queries the database directly to show:
    - Total conversations in database
    - Total completed tasks in database
    - Total persons
    - Total activity summaries
    - Latest sync timestamps

    This works without needing Celery task status.
    """
    from src.db.database import AsyncSessionLocal
    from src.schemas.person import ConversationActivity, TaskActivity, ActivitySummary, Person
    from sqlalchemy import select, func

    try:
        async with AsyncSessionLocal() as session:
            # Count conversations
            conv_result = await session.execute(select(func.count(ConversationActivity.id)))
            total_conversations = conv_result.scalar_one()

            # Count tasks
            task_result = await session.execute(select(func.count(TaskActivity.id)))
            total_tasks = task_result.scalar_one()

            # Count persons
            person_result = await session.execute(select(func.count(Person.id)))
            total_persons = person_result.scalar_one()

            # Count summaries
            summary_result = await session.execute(select(func.count(ActivitySummary.person_id)))
            total_summaries = summary_result.scalar_one()

            # Get latest conversation sync
            latest_conv = await session.execute(
                select(ConversationActivity.last_synced_at)
                .order_by(ConversationActivity.last_synced_at.desc())
                .limit(1)
            )
            latest_conv_sync = latest_conv.scalar_one_or_none()

            # Get latest task sync
            latest_task = await session.execute(
                select(TaskActivity.last_synced_at)
                .order_by(TaskActivity.last_synced_at.desc())
                .limit(1)
            )
            latest_task_sync = latest_task.scalar_one_or_none()

            # Get latest summary update
            latest_summary = await session.execute(
                select(ActivitySummary.updated_at)
                .order_by(ActivitySummary.updated_at.desc())
                .limit(1)
            )
            latest_summary_update = latest_summary.scalar_one_or_none()

            return {
                "status": "success",
                "database_stats": {
                    "total_conversations": total_conversations,
                    "total_completed_tasks": total_tasks,
                    "total_persons": total_persons,
                    "total_activity_summaries": total_summaries
                },
                "latest_sync_times": {
                    "latest_conversation_sync": latest_conv_sync.isoformat() if latest_conv_sync else None,
                    "latest_task_sync": latest_task_sync.isoformat() if latest_task_sync else None,
                    "latest_summary_update": latest_summary_update.isoformat() if latest_summary_update else None
                }
            }

    except Exception as e:
        logger.error("failed_to_get_sync_stats", error=str(e))
        return {
            "status": "error",
            "message": f"Failed to get sync stats: {str(e)}"
        }

"""
Celery application instance for background task processing.
Handles periodic cache updates for Notion data.
"""
from celery import Celery
from celery.schedules import crontab
from src.core.config import settings

# Create Celery app
celery_app = Celery(
    "notion_stats",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["src.tasks.notion_cache_tasks"]
)

# Celery configuration
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_backend=settings.celery_backend,  # Explicitly set result backend
    result_expires=3600,  # Results expire after 1 hour
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # Soft limit at 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Periodic task schedule - runs every 30 minutes
celery_app.conf.beat_schedule = {
    "update-notion-projects-cache": {
        "task": "src.tasks.notion_cache_tasks.update_projects_cache",
        "schedule": crontab(minute=f"*/{settings.CACHE_UPDATE_INTERVAL_MINUTES}"),
    },
    "update-notion-tasks-cache": {
        "task": "src.tasks.notion_cache_tasks.update_tasks_cache",
        "schedule": crontab(minute=f"*/{settings.CACHE_UPDATE_INTERVAL_MINUTES}"),
    },
    "update-notion-todos-cache": {
        "task": "src.tasks.notion_cache_tasks.update_todos_cache",
        "schedule": crontab(minute=f"*/{settings.CACHE_UPDATE_INTERVAL_MINUTES}"),
    },
    # Activity sync task - run every 12 hours (full sync of conversations and completed tasks)
    "update-notion-activities-cache": {
        "task": "src.tasks.notion_cache_tasks.update_activities_cache",
        "schedule": crontab(hour="*/12", minute="0"),  # Every 12 hours at :00 (0:00, 12:00)
    },
}

if __name__ == "__main__":
    celery_app.start()

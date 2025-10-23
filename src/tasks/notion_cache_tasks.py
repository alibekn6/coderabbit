"""
Celery tasks for updating Notion data cache.
These tasks run periodically in the background to keep cached data fresh.

Logic Flow:
1. Celery Beat schedules task every 30 minutes
2. Celery Worker executes task
3. Task calls NotionService to fetch data from Notion API (same as API endpoints!)
4. Task converts Pydantic models to SQLAlchemy models
5. Task saves to PostgreSQL cache using existing async connector
6. API reads from cache (fast!)
"""
import time
import asyncio
from datetime import datetime

from src.celery_app import celery_app
from src.core.config import settings
from src.repositories.cache_repository import CacheRepository
from src.schemas.notion_cache import (
    CachedNotionProject,
    CachedNotionTask,
    CachedNotionTodo
)

# Import NotionService - the SAME service used by API endpoints!
from src.services.notion_service import NotionService

# Import ActivitySyncService for syncing conversations and completed tasks
from src.services.activity_sync_service import ActivitySyncService

# Import ActivityStatsService for aggregating daily summaries
from src.services.activity_stats_service import ActivityStatsService

# Use sync database connector for cache operations
from src.db.sync_database import get_sync_session

# Import async database session for activity sync
from src.db.database import AsyncSessionLocal


def run_async(coro):
    """
    Helper to run async functions in Celery tasks.
    NotionService is async, but database operations are now sync.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="src.tasks.notion_cache_tasks.update_projects_cache", bind=True, max_retries=3)
def update_projects_cache(self):
    """
    Celery task to update projects cache from Notion.
    Runs every 30 minutes (configured in celery_app.py)
    
    Uses NotionService.get_all_projects() - same method as API!
    Uses sync database connector for cache operations!
    """
    # Get sync database session
    db = get_sync_session()
    cache_repo = CacheRepository(db)
    cache_type = "projects"
    
    try:
        # Check if already updating
        metadata = cache_repo.get_cache_metadata(cache_type)
        if metadata and metadata.is_updating:
            print(f"[{cache_type}] Already updating, skipping...")
            return {"status": "skipped", "reason": "already_updating"}
        
        # Mark as updating
        cache_repo.set_cache_updating(cache_type, True)
        
        start_time = time.time()
        print(f"[{cache_type}] Starting cache update...")
        
        # Fetch fresh data from Notion using NotionService (async)
        notion_service = NotionService()
        projects_response = run_async(notion_service.get_all_projects())
        
        # Clear old cache
        cache_repo.clear_projects_cache()
        
        # Convert Pydantic models to SQLAlchemy cache models
        cached_projects = []
        for project in projects_response.projects:
            # Parse created_time and last_edited_time (might be string or datetime)
            if isinstance(project.created_time, str):
                created_time = datetime.fromisoformat(project.created_time.replace("Z", "+00:00"))
            else:
                created_time = project.created_time
                
            if isinstance(project.last_edited_time, str):
                last_edited_time = datetime.fromisoformat(project.last_edited_time.replace("Z", "+00:00"))
            else:
                last_edited_time = project.last_edited_time
            
            cached_project = CachedNotionProject(
                page_id=project.page_id,
                project_name=project.properties.project_name,
                health_status=project.properties.health_status,
                health_color=project.properties.health_color,
                status=project.properties.status,
                priority=project.properties.priority,
                priority_color=project.properties.priority_color,
                assignees=project.properties.assignees,  # List stored as JSONB
                task_count=project.properties.task_count,
                url=project.url,
                notion_created_time=created_time,
                notion_last_edited_time=last_edited_time,
            )
            cached_projects.append(cached_project)
        
        # Bulk insert into PostgreSQL
        cache_repo.bulk_insert_projects(cached_projects)
        
        # Update metadata
        duration = int(time.time() - start_time)
        cache_repo.update_cache_metadata(
            cache_type=cache_type,
            total_records=len(cached_projects),
            update_duration_seconds=duration,
            error_message=None
        )
        
        print(f"[{cache_type}] Cache updated successfully! {len(cached_projects)} projects in {duration}s")
        
        return {
            "status": "success",
            "total_records": len(cached_projects),
            "duration_seconds": duration
        }
        
    except Exception as exc:
        duration = int(time.time() - start_time) if 'start_time' in locals() else 0
        error_msg = str(exc)
        
        # Update metadata with error
        cache_repo.update_cache_metadata(
            cache_type=cache_type,
            total_records=0,
            update_duration_seconds=duration,
            error_message=error_msg
        )
        
        print(f"[{cache_type}] Error updating cache: {error_msg}")
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()


@celery_app.task(name="src.tasks.notion_cache_tasks.update_tasks_cache", bind=True, max_retries=3)
def update_tasks_cache(self):
    """
    Celery task to update tasks cache from Notion.
    Runs every 30 minutes (configured in celery_app.py)
    
    Uses NotionService.get_all_tasks() - same method as API!
    Uses sync database connector for cache operations!
    """
    # Get sync database session
    db = get_sync_session()
    cache_repo = CacheRepository(db)
    cache_type = "tasks"
    
    try:
        # Check if already updating
        metadata = cache_repo.get_cache_metadata(cache_type)
        if metadata and metadata.is_updating:
            print(f"[{cache_type}] Already updating, skipping...")
            return {"status": "skipped", "reason": "already_updating"}
        
        # Mark as updating
        cache_repo.set_cache_updating(cache_type, True)
        
        start_time = time.time()
        print(f"[{cache_type}] Starting cache update...")
        
        # Fetch fresh data from Notion using NotionService (async)
        notion_service = NotionService()
        tasks_response = run_async(notion_service.get_all_tasks())
        
        # Clear old cache
        cache_repo.clear_tasks_cache()
        
        # Convert Pydantic models to SQLAlchemy cache models
        cached_tasks = []
        for task in tasks_response.tasks:
            # Parse due_date if it's a string
            due_date = None
            if task.properties.due_date:
                if isinstance(task.properties.due_date, str):
                    try:
                        due_date = datetime.fromisoformat(task.properties.due_date.replace("Z", "+00:00")).date()
                    except Exception:
                        due_date = None
                else:
                    due_date = task.properties.due_date
            
            # Parse created_time and last_edited_time (might be string or datetime)
            if isinstance(task.created_time, str):
                created_time = datetime.fromisoformat(task.created_time.replace("Z", "+00:00"))
            else:
                created_time = task.created_time
                
            if isinstance(task.last_edited_time, str):
                last_edited_time = datetime.fromisoformat(task.last_edited_time.replace("Z", "+00:00"))
            else:
                last_edited_time = task.last_edited_time
            
            cached_task = CachedNotionTask(
                page_id=task.page_id,
                task_name=task.properties.task_name,
                status=task.properties.status,
                priority=task.properties.priority,
                effort_level=task.properties.effort_level,
                description=task.properties.description,
                due_date=due_date,
                task_type=task.properties.task_type,  # List stored as JSONB
                assignee=task.properties.assignee,  # List stored as JSONB
                notion_created_time=created_time,
                notion_last_edited_time=last_edited_time,
            )
            cached_tasks.append(cached_task)
        
        # Bulk insert into PostgreSQL
        cache_repo.bulk_insert_tasks(cached_tasks)
        
        # Update metadata
        duration = int(time.time() - start_time)
        cache_repo.update_cache_metadata(
            cache_type=cache_type,
            total_records=len(cached_tasks),
            update_duration_seconds=duration,
            error_message=None
        )
        
        print(f"[{cache_type}] Cache updated successfully! {len(cached_tasks)} tasks in {duration}s")
        
        return {
            "status": "success",
            "total_records": len(cached_tasks),
            "duration_seconds": duration
        }
        
    except Exception as exc:
        duration = int(time.time() - start_time) if 'start_time' in locals() else 0
        error_msg = str(exc)
        
        # Update metadata with error
        cache_repo.update_cache_metadata(
            cache_type=cache_type,
            total_records=0,
            update_duration_seconds=duration,
            error_message=error_msg
        )
        
        print(f"[{cache_type}] Error updating cache: {error_msg}")
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()


@celery_app.task(name="src.tasks.notion_cache_tasks.update_todos_cache", bind=True, max_retries=3)
def update_todos_cache(self):
    """
    Celery task to update todos cache from Notion.
    Runs every 30 minutes (configured in celery_app.py)
    
    Uses NotionService.get_all_member_todos() - same method as API!
    Uses sync database connector for cache operations!
    """
    # Get sync database session
    db = get_sync_session()
    cache_repo = CacheRepository(db)
    cache_type = "todos"
    
    try:
        # Check if already updating
        metadata = cache_repo.get_cache_metadata(cache_type)
        if metadata and metadata.is_updating:
            print(f"[{cache_type}] Already updating, skipping...")
            return {"status": "skipped", "reason": "already_updating"}
        
        # Mark as updating
        cache_repo.set_cache_updating(cache_type, True)
        
        start_time = time.time()
        print(f"[{cache_type}] Starting cache update...")
        
        # Fetch fresh data from Notion using NotionService (async)
        notion_service = NotionService()
        todos_response = run_async(notion_service.get_all_member_todos(status_filter=None))
        
        # Clear old cache
        cache_repo.clear_todos_cache()
        
        # Convert Pydantic models to SQLAlchemy cache models
        # Use dict to deduplicate by todo_id (same todo might appear in multiple members' boards)
        todos_dict = {}
        
        for member_with_todos in todos_response.members:
            member_info = member_with_todos.member
            
            # Create or update team member
            cache_repo.get_or_create_team_member(
                member_name=member_info.name,
                position=member_info.position,
                status=member_info.status,
                tg_id=member_info.tg_id,
                start_date=member_info.start_date
            )
            
            # Add todos for this member
            for todo in member_with_todos.todos:
                # Skip if we've already processed this todo
                if todo.id in todos_dict:
                    continue
                
                # Parse dates
                deadline = None
                if todo.properties.deadline:
                    if isinstance(todo.properties.deadline, str):
                        try:
                            deadline = datetime.fromisoformat(todo.properties.deadline.replace("Z", "+00:00")).date()
                        except Exception:
                            deadline = None
                    else:
                        deadline = todo.properties.deadline
                
                date_done = None
                if todo.properties.date_done:
                    if isinstance(todo.properties.date_done, str):
                        try:
                            date_done = datetime.fromisoformat(todo.properties.date_done.replace("Z", "+00:00")).date()
                        except Exception:
                            date_done = None
                    else:
                        date_done = todo.properties.date_done
                
                cached_todo = CachedNotionTodo(
                    todo_id=todo.id,
                    member_name=member_info.name,
                    task_name=todo.properties.name,
                    status=todo.properties.status,
                    deadline=deadline,
                    date_done=date_done,
                    is_overdue=todo.properties.is_overdue,
                    project_ids=todo.properties.project_ids,  # List stored as JSONB
                    url=todo.url,
                )
                todos_dict[todo.id] = cached_todo
        
        # Convert dict to list for bulk insert
        cached_todos = list(todos_dict.values())
        
        # Bulk insert into PostgreSQL
        cache_repo.bulk_insert_todos(cached_todos)
        
        # Update metadata
        duration = int(time.time() - start_time)
        cache_repo.update_cache_metadata(
            cache_type=cache_type,
            total_records=len(cached_todos),
            update_duration_seconds=duration,
            error_message=None
        )
        
        print(f"[{cache_type}] Cache updated successfully! {len(cached_todos)} todos in {duration}s")
        
        return {
            "status": "success",
            "total_records": len(cached_todos),
            "duration_seconds": duration
        }
        
    except Exception as exc:
        duration = int(time.time() - start_time) if 'start_time' in locals() else 0
        error_msg = str(exc)
        
        # Rollback the transaction if there was an error
        db.rollback()
        
        # Update metadata with error
        try:
            cache_repo.update_cache_metadata(
                cache_type=cache_type,
                total_records=0,
                update_duration_seconds=duration,
                error_message=error_msg
            )
        except Exception:
            # If metadata update also fails, just log it
            print(f"[{cache_type}] Failed to update metadata after error: {error_msg}")

        print(f"[{cache_type}] Error updating cache: {error_msg}")

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    finally:
        db.close()


@celery_app.task(name="src.tasks.notion_cache_tasks.update_activities_cache", bind=True, max_retries=3)
def update_activities_cache(self):
    """
    Celery task to update activities cache from Notion.
    Runs every 12 hours (configured in celery_app.py)

    Uses ActivitySyncService.sync_all() to fetch ALL conversations and completed tasks (full sync).
    Then aggregates daily summaries for the entire year for each person.
    Syncs to conversation_activities, task_activities, and activity_summaries tables in PostgreSQL.
    """
    cache_type = "activities"
    start_time = time.time()

    try:
        print(f"[{cache_type}] Starting full sync of conversations and completed tasks...")

        # Use async database session for activity sync
        async def sync_and_aggregate_activities():
            from datetime import date

            async with AsyncSessionLocal() as session:
                # Step 1: Sync all activities from Notion
                sync_service = ActivitySyncService(session)
                result = await sync_service.sync_all(incremental=False)
                await session.commit()

                # Step 2: Aggregate daily summaries for the entire year
                print(f"[{cache_type}] Aggregating daily summaries for the entire year...")
                aggregation_start = time.time()

                stats_service = ActivityStatsService(session)

                # Calculate date range: from start of current year to today
                today = date.today()
                start_of_year = today.replace(month=1, day=1)

                summaries_count = await stats_service.bulk_aggregate_daily_activities(
                    start_date=start_of_year,
                    end_date=today
                )

                aggregation_duration = int(time.time() - aggregation_start)
                print(f"[{cache_type}] Aggregation completed: {summaries_count} summaries created/updated in {aggregation_duration}s")

                result['summaries_created'] = summaries_count
                result['aggregation_duration_seconds'] = aggregation_duration

                return result

        # Run async sync and aggregation
        result = run_async(sync_and_aggregate_activities())

        duration = int(time.time() - start_time)

        print(f"[{cache_type}] Full sync and aggregation completed in {duration}s")
        print(f"[{cache_type}] Conversations synced: {result['conversations_synced']}")
        print(f"[{cache_type}] Completed tasks synced: {result['tasks_synced']}")
        print(f"[{cache_type}] Persons created: {result['persons_created']}, Persons updated: {result['persons_updated']}")
        print(f"[{cache_type}] Daily summaries: {result['summaries_created']}")

        if result.get('errors'):
            print(f"[{cache_type}] Errors: {result['errors']}")

        return {
            "status": "success",
            "conversations_synced": result['conversations_synced'],
            "tasks_synced": result['tasks_synced'],
            "persons_created": result['persons_created'],
            "persons_updated": result['persons_updated'],
            "summaries_created": result['summaries_created'],
            "errors": result.get('errors', []),
            "duration_seconds": duration
        }

    except Exception as exc:
        duration = int(time.time() - start_time) if 'start_time' in locals() else 0
        error_msg = str(exc)

        print(f"[{cache_type}] Error during sync: {error_msg}")

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

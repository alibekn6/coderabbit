#!/usr/bin/env python3
"""
Script to manually initialize or refresh the Notion cache.
Run this to populate cache immediately instead of waiting for scheduled updates.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tasks.notion_cache_tasks import (
    update_projects_cache,
    update_tasks_cache,
    update_todos_cache
)


def main():
    print("🚀 Initializing Notion cache...")
    print("=" * 60)
    
    # Queue cache update tasks
    print("\n📊 Queueing projects cache update...")
    result1 = update_projects_cache.delay()
    print(f"   Task ID: {result1.id}")
    
    print("\n📋 Queueing tasks cache update...")
    result2 = update_tasks_cache.delay()
    print(f"   Task ID: {result2.id}")
    
    print("\n✅ Queueing todos cache update...")
    result3 = update_todos_cache.delay()
    print(f"   Task ID: {result3.id}")
    
    print("\n" + "=" * 60)
    print("✨ All cache update tasks have been queued!")
    print("\nℹ️  Tasks are running in the background.")
    print("   Monitor progress in Celery worker logs.")
    print("\nℹ️  Check cache status via API:")
    print("   GET /api/v1/cache-info/projects")
    print("   GET /api/v1/cache-info/tasks")
    print("   GET /api/v1/cache-info/todos")
    print("\n⏱  Expect updates to complete in 3-5 minutes...")


if __name__ == "__main__":
    main()

"""
Sync activities from Notion databases.

This script can be run as a standalone command or scheduled as a cron job
to periodically sync activities from Notion.

Database IDs are read from environment variables:
- NOTION_CONVERSATION_DATABASE_ID
- NOTION_KANBAN_DATABASE_ID

Usage:
    python -m src.notion_fetching.sync_activities [--no-aggregate] [--full-sync]
"""

import asyncio
import argparse
from datetime import datetime
from src.db.database import AsyncSessionLocal
from src.services.activity_sync_service import ActivitySyncService
from src.services.activity_stats_service import ActivityStatsService
from src.core.logging import get_logger

logger = get_logger(__name__)


async def sync_and_aggregate(
    aggregate: bool = True,
    incremental: bool = True
):
    """
    Sync activities from Notion and optionally aggregate statistics.

    Database IDs are read from config (NOTION_CONVERSATION_DATABASE_ID, NOTION_KANBAN_DATABASE_ID).

    Args:
        aggregate: Run daily aggregation after sync
        incremental: Only sync recent changes
    """
    start_time = datetime.utcnow()

    logger.info(
        "sync_started",
        aggregate=aggregate,
        incremental=incremental
    )

    async with AsyncSessionLocal() as session:
        try:
            # Sync activities
            sync_service = ActivitySyncService(session)
            sync_result = await sync_service.sync_all(
                incremental=incremental
            )

            logger.info("sync_completed", result=sync_result)

            print("\n" + "=" * 80)
            print("SYNC RESULTS")
            print("=" * 80)
            print(f"Conversations synced: {sync_result['conversations_synced']}")
            print(f"Tasks synced: {sync_result['tasks_synced']}")
            print(f"Persons created: {sync_result['persons_created']}")
            print(f"Persons updated: {sync_result['persons_updated']}")
            print(f"Duration: {sync_result['sync_duration_seconds']:.2f}s")

            if sync_result.get("errors"):
                print(f"\nErrors ({len(sync_result['errors'])}):")
                for error in sync_result["errors"]:
                    print(f"  - {error}")

            # Aggregate daily statistics
            if aggregate:
                print("\n" + "=" * 80)
                print("AGGREGATING DAILY STATISTICS")
                print("=" * 80)

                stats_service = ActivityStatsService(session)

                # Aggregate for today
                from datetime import date
                today = date.today()

                count = await stats_service.bulk_aggregate_daily_activities(
                    start_date=today, end_date=today
                )

                logger.info("aggregation_completed", summaries_created=count)
                print(f"Summaries created/updated: {count}")

            duration = (datetime.utcnow() - start_time).total_seconds()
            print("\n" + "=" * 80)
            print(f"TOTAL DURATION: {duration:.2f}s")
            print("=" * 80 + "\n")

        except Exception as e:
            logger.error("sync_failed", error=str(e))
            print(f"\n❌ Sync failed: {str(e)}")
            raise


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync activities from Notion databases (uses database IDs from config)"
    )
    parser.add_argument(
        "--no-aggregate",
        action="store_true",
        help="Skip daily aggregation"
    )
    parser.add_argument(
        "--full-sync",
        action="store_true",
        help="Perform full sync (not incremental)"
    )

    args = parser.parse_args()

    await sync_and_aggregate(
        aggregate=not args.no_aggregate,
        incremental=not args.full_sync
    )


if __name__ == "__main__":
    asyncio.run(main())

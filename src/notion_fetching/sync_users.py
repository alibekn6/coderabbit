"""
Sync users from Notion users database to local Person table.

This script fetches all users from NOTION_USERS_DATABASE_ID and creates
or updates them in the local database.

Usage:
    python -m src.notion_fetching.sync_users
"""

import asyncio
from datetime import datetime
from src.db.database import AsyncSessionLocal
from src.repositories.person_repository import PersonRepository
from src.core.config import Config
from src.core.logging import get_logger
from notion_client import AsyncClient

logger = get_logger(__name__)
config = Config()


async def sync_users_from_notion(users_database_id: str):
    """
    Sync all users from Notion users database.
    
    Args:
        users_database_id: Notion database ID for users
        
    Returns:
        Sync statistics
    """
    start_time = datetime.utcnow()
    stats = {
        "users_processed": 0,
        "users_created": 0,
        "users_updated": 0,
        "errors": []
    }
    
    logger.info("sync_users_started", database_id=users_database_id)
    
    async with AsyncSessionLocal() as session:
        try:
            # Initialize Notion client and repository
            notion = AsyncClient(auth=config.NOTION_API_KEY)
            person_repo = PersonRepository(session)
            
            # Query Notion users database
            has_more = True
            start_cursor = None
            all_users = []
            
            print(f"\n🔄 Fetching users from Notion database: {users_database_id}")
            
            while has_more:
                query_params = {
                    "database_id": users_database_id,
                    "page_size": 100
                }
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                response = await notion.databases.query(**query_params)
                all_users.extend(response.get("results", []))
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            logger.info("users_fetched_from_notion", count=len(all_users))
            print(f"✅ Fetched {len(all_users)} users from Notion\n")
            
            # Process each user
            for user_page in all_users:
                try:
                    page_id = user_page["id"]
                    properties = user_page.get("properties", {})
                    
                    # Extract user data
                    username = extract_name(properties)
                    email = extract_email(properties)
                    telegram_id = extract_telegram_id(properties)
                    notion_user_id = extract_notion_user_id(properties)
                    
                    # Use page creator as notion_id if not specified
                    avatar_url = None
                    if not notion_user_id:
                        created_by = user_page.get("created_by", {})
                        notion_user_id = created_by.get("id")
                        avatar_url = created_by.get("avatar_url")
                    
                    if not notion_user_id:
                        logger.warning("user_no_notion_id", page_id=page_id)
                        stats["errors"].append(f"No Notion ID for page {page_id}")
                        continue
                    
                    # Get or create person
                    person, created = await person_repo.get_or_create_by_notion_id(
                        notion_id=notion_user_id,
                        username=username or "Unknown User",
                        avatar_url=avatar_url,
                        email=email
                    )
                    
                    # Update telegram_id if provided and different
                    if telegram_id and person.telegram_id != telegram_id:
                        await person_repo.update(
                            person_id=person.id,
                            telegram_id=telegram_id
                        )
                    
                    stats["users_processed"] += 1
                    if created:
                        stats["users_created"] += 1
                        print(f"✨ Created: {username} ({email or 'no email'})")
                    else:
                        stats["users_updated"] += 1
                        print(f"🔄 Updated: {username} ({email or 'no email'})")
                    
                    logger.info(
                        "user_synced",
                        person_id=person.id,
                        notion_id=notion_user_id,
                        created=created
                    )
                    
                except Exception as e:
                    error_msg = f"Error processing user {user_page.get('id')}: {str(e)}"
                    logger.error("user_processing_error", error=error_msg)
                    stats["errors"].append(error_msg)
                    print(f"❌ Error: {error_msg}")
            
            # Commit all changes
            await session.commit()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info("sync_users_completed", stats=stats, duration=duration)
            
            # Print summary
            print("\n" + "=" * 80)
            print("SYNC SUMMARY")
            print("=" * 80)
            print(f"Users processed: {stats['users_processed']}")
            print(f"Users created: {stats['users_created']}")
            print(f"Users updated: {stats['users_updated']}")
            print(f"Errors: {len(stats['errors'])}")
            print(f"Duration: {duration:.2f}s")
            print("=" * 80 + "\n")
            
            if stats["errors"]:
                print("\n⚠️  ERRORS:")
                for error in stats["errors"]:
                    print(f"  - {error}")
            
            return {**stats, "sync_duration_seconds": duration}
            
        except Exception as e:
            logger.error("sync_users_failed", error=str(e))
            print(f"\n❌ Sync failed: {str(e)}")
            await session.rollback()
            raise


def extract_name(properties: dict) -> str:
    """Extract user name from Notion properties."""
    # Try common name property names
    for prop_name in ["Name", "Имя", "Full Name", "Username", "Название"]:
        if prop_name in properties:
            prop = properties[prop_name]
            
            # Title property
            if prop.get("title"):
                return "".join([t["plain_text"] for t in prop["title"]])
            
            # Rich text property
            if prop.get("rich_text"):
                return "".join([t["plain_text"] for t in prop["rich_text"]])
    
    return "Unknown User"


def extract_email(properties: dict) -> str | None:
    """Extract email from Notion properties."""
    for prop_name in ["Email", "Почта", "E-mail"]:
        if prop_name in properties:
            prop = properties[prop_name]
            
            # Email property type
            if prop.get("email"):
                return prop["email"]
            
            # Rich text or title
            if prop.get("rich_text"):
                text = "".join([t["plain_text"] for t in prop["rich_text"]])
                if "@" in text:
                    return text.strip()
            
            if prop.get("title"):
                text = "".join([t["plain_text"] for t in prop["title"]])
                if "@" in text:
                    return text.strip()
    
    return None


def extract_telegram_id(properties: dict) -> str | None:
    """Extract Telegram ID from Notion properties."""
    for prop_name in ["Telegram", "Telegram ID", "TG", "TG ID"]:
        if prop_name in properties:
            prop = properties[prop_name]
            
            if prop.get("rich_text"):
                return "".join([t["plain_text"] for t in prop["rich_text"]])
            
            if prop.get("title"):
                return "".join([t["plain_text"] for t in prop["title"]])
    
    return None


def extract_notion_user_id(properties: dict) -> str | None:
    """Extract Notion User ID from Notion properties (if stored in a property)."""
    for prop_name in ["Notion ID", "User ID", "NotionID"]:
        if prop_name in properties:
            prop = properties[prop_name]
            
            # People property
            if prop.get("people") and len(prop["people"]) > 0:
                return prop["people"][0].get("id")
            
            # Rich text
            if prop.get("rich_text"):
                return "".join([t["plain_text"] for t in prop["rich_text"]])
    
    return None


async def main():
    """Main entry point."""
    # Add NOTION_USERS_DATABASE_ID to config if not present
    users_db_id = "1c33b84f-1fac-80e7-8028-e7d1713b96d1"
    
    print("\n" + "=" * 80)
    print("NOTION USERS SYNC")
    print("=" * 80)
    print(f"Database ID: {users_db_id}\n")
    
    await sync_users_from_notion(users_db_id)


if __name__ == "__main__":
    asyncio.run(main())


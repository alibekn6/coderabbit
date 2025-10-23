"""
Activity sync service for syncing activities from Notion.

This service handles syncing conversation and task activities from Notion databases.
"""

from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from notion_client import AsyncClient
from src.repositories.person_repository import PersonRepository
from src.repositories.activity_repository import ActivityRepository
from src.core.config import Config
from src.core.logging import get_logger

logger = get_logger(__name__)
config = Config()


class ActivitySyncService:
    """Service for syncing activities from Notion databases."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.person_repo = PersonRepository(session)
        self.activity_repo = ActivityRepository(session)
        self.notion = AsyncClient(auth=config.NOTION_API_KEY)

    async def sync_all(
        self,
        incremental: bool = True
    ) -> Dict:
        """
        Sync all activities from Notion databases.

        Uses database IDs from config (NOTION_CONVERSATION_DATABASE_ID, NOTION_KANBAN_DATABASE_ID).

        Args:
            incremental: Only sync recent changes if True

        Returns:
            Sync statistics
        """
        start_time = datetime.utcnow()
        stats = {
            "conversations_synced": 0,
            "tasks_synced": 0,
            "persons_created": 0,
            "persons_updated": 0,
            "errors": []
        }

        try:
            # Get database IDs from config
            conversation_db_id = config.NOTION_CONVERSATION_DATABASE_ID
            kanban_db_id = config.NOTION_KANBAN_DATABASE_ID

            # Sync conversations
            if conversation_db_id:
                logger.info("syncing_conversations_from_db", database_id=conversation_db_id)
                conv_stats = await self.sync_conversations(
                    conversation_db_id, incremental
                )
                stats["conversations_synced"] = conv_stats["synced"]
                stats["persons_created"] += conv_stats["persons_created"]
                stats["persons_updated"] += conv_stats["persons_updated"]
                stats["errors"].extend(conv_stats["errors"])
            else:
                logger.warning("no_conversation_database_id_in_config")

            # Sync tasks
            if kanban_db_id:
                logger.info("syncing_tasks_from_db", database_id=kanban_db_id)
                task_stats = await self.sync_tasks(kanban_db_id, incremental)
                stats["tasks_synced"] = task_stats["synced"]
                stats["persons_created"] += task_stats["persons_created"]
                stats["persons_updated"] += task_stats["persons_updated"]
                stats["errors"].extend(task_stats["errors"])
            else:
                logger.warning("no_kanban_database_id_in_config")

            await self.session.commit()

        except Exception as e:
            logger.error("sync_all_failed", error=str(e))
            stats["errors"].append(f"Sync failed: {str(e)}")
            await self.session.rollback()

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info("sync_completed", stats=stats, duration=duration)

        return {**stats, "sync_duration_seconds": duration}

    async def sync_conversations(
        self, database_id: str, incremental: bool = True
    ) -> Dict:
        """
        Sync conversation activities from Notion conversation_db.

        Args:
            database_id: Notion database ID for conversations
            incremental: Only sync recent changes if True

        Returns:
            Sync statistics
        """
        logger.info("syncing_conversations", database_id=database_id)

        stats = {
            "synced": 0,
            "persons_created": 0,
            "persons_updated": 0,
            "errors": []
        }

        try:
            # Query Notion database
            has_more = True
            start_cursor = None
            all_pages = []

            while has_more:
                query_params = {"database_id": database_id, "page_size": 100}
                if start_cursor:
                    query_params["start_cursor"] = start_cursor

                response = await self.notion.databases.query(**query_params)
                all_pages.extend(response.get("results", []))
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")

            logger.info("conversations_fetched", count=len(all_pages))

            # Process each conversation
            conversation_activities = []
            persons_to_create = []

            for page in all_pages:
                try:
                    # Extract conversation data
                    page_id = page["id"]
                    created_time = datetime.fromisoformat(
                        page["created_time"].replace("Z", "+00:00")
                    )
                    properties = page.get("properties", {})

                    # Get conversation title
                    title = self._extract_title(properties)

                    # Get attendees (people who participated in the conversation)
                    attendees = self._extract_people(properties)
                    
                    # If no attendees field, try to parse from title
                    if not attendees and title:
                        # Extract attendee name from title (format: "Name - Description")
                        attendee_name = self._parse_attendee_from_title(title)
                        
                        if attendee_name:
                            # Try to find person by name in database
                            try:
                                from src.repositories.person_repository import PersonRepository
                                person_repo_local = PersonRepository(self.activity_repo.session)
                                persons, _ = await person_repo_local.get_all(search=attendee_name, limit=1)
                                
                                if persons:
                                    person = persons[0]
                                    attendees = [{
                                        "id": person.notion_id,
                                        "name": person.username,
                                        "avatar_url": person.avatar_url
                                    }]
                                    logger.info("attendee_parsed_from_title", 
                                              title=title, 
                                              attendee=attendee_name,
                                              person_id=person.id)
                            except Exception as e:
                                logger.warning("failed_to_parse_attendee", title=title, error=str(e))
                    
                    # If still no attendees, fall back to creator
                    if not attendees:
                        created_by = page.get("created_by", {})
                        creator_id = created_by.get("id")
                        creator_name = created_by.get("name", "Unknown")
                        
                        if creator_id:
                            attendees = [{
                                "id": creator_id,
                                "name": creator_name,
                                "avatar_url": created_by.get("avatar_url")
                            }]
                    
                    if not attendees:
                        logger.warning("conversation_no_attendees", page_id=page_id)
                        continue

                    # Create one activity per attendee
                    for attendee_data in attendees:
                        attendee_id = attendee_data["id"]
                        attendee_name = attendee_data["name"]
                        avatar_url = attendee_data.get("avatar_url")

                        # Get or create person
                        person, created = await self.person_repo.get_or_create_by_notion_id(
                            notion_id=attendee_id,
                            username=attendee_name,
                            avatar_url=avatar_url
                        )

                        if created:
                            stats["persons_created"] += 1
                        else:
                            stats["persons_updated"] += 1

                        # Prepare conversation activity
                        conversation_activities.append({
                            "person_id": person.id,
                            "notion_conversation_id": page_id,
                            "conversation_title": title,
                            "created_at": created_time,
                            "notion_metadata": {
                                "notion_url": page.get("url"),
                                "properties": properties
                            }
                        })

                except Exception as e:
                    error_msg = f"Error processing conversation {page.get('id')}: {str(e)}"
                    logger.error("conversation_processing_error", error=error_msg)
                    stats["errors"].append(error_msg)

            # Bulk create conversations
            if conversation_activities:
                created = await self.activity_repo.bulk_create_conversations(
                    conversation_activities
                )
                stats["synced"] = len(created)

        except Exception as e:
            error_msg = f"Error syncing conversations: {str(e)}"
            logger.error("sync_conversations_failed", error=error_msg)
            stats["errors"].append(error_msg)

        return stats

    async def sync_tasks(self, database_id: str, incremental: bool = True) -> Dict:
        """
        Sync task completions from Notion Kanban database.

        Only syncs tasks with status = "Done".

        Args:
            database_id: Notion database ID for Kanban
            incremental: Only sync recent changes if True

        Returns:
            Sync statistics
        """
        logger.info("syncing_tasks", database_id=database_id)

        stats = {
            "synced": 0,
            "persons_created": 0,
            "persons_updated": 0,
            "errors": []
        }

        try:
            # Query Notion database for "Done" tasks
            has_more = True
            start_cursor = None
            all_pages = []

            while has_more:
                query_params = {"database_id": database_id, "page_size": 100}
                if start_cursor:
                    query_params["start_cursor"] = start_cursor

                response = await self.notion.databases.query(**query_params)
                all_pages.extend(response.get("results", []))
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")

            logger.info("tasks_fetched", count=len(all_pages))

            # Process each task
            task_activities = []

            for page in all_pages:
                try:
                    page_id = page["id"]
                    properties = page.get("properties", {})
                    last_edited_time = datetime.fromisoformat(
                        page["last_edited_time"].replace("Z", "+00:00")
                    )

                    # Check status
                    status_prop = properties.get("Status", {})
                    status_name = None
                    if status_prop.get("select"):
                        status_name = status_prop["select"].get("name")
                    elif status_prop.get("status"):
                        status_name = status_prop["status"].get("name")

                    # Only process "Done" tasks
                    if status_name != "Done":
                        continue

                    # Get completion date from "Date Done" property (NOT last_edited_time!)
                    completed_at = None
                    date_done_prop = properties.get("Date Done", {})
                    if date_done_prop.get("date") and date_done_prop["date"].get("start"):
                        try:
                            completed_at = datetime.fromisoformat(
                                date_done_prop["date"]["start"].replace("Z", "+00:00")
                            )
                        except Exception as e:
                            logger.warning("failed_to_parse_date_done", page_id=page_id, error=str(e))
                    
                    # Fallback to last_edited_time if Date Done is not available
                    if not completed_at:
                        completed_at = last_edited_time
                        logger.warning("using_last_edited_time_fallback", page_id=page_id, title=properties.get("Name", {}).get("title", [{}])[0].get("plain_text", "Unknown"))

                    # Get task title
                    title = self._extract_title(properties)

                    # Get project name
                    project_name = self._extract_project(properties)

                    # Get assigned person
                    assigned_people = self._extract_people(properties)

                    if not assigned_people:
                        logger.warning("task_no_assignee", page_id=page_id)
                        continue

                    # Process each assigned person
                    for person_data in assigned_people:
                        person_id = person_data["id"]
                        person_name = person_data["name"]
                        avatar_url = person_data.get("avatar_url")

                        # Get or create person
                        person, created = await self.person_repo.get_or_create_by_notion_id(
                            notion_id=person_id,
                            username=person_name,
                            avatar_url=avatar_url
                        )

                        if created:
                            stats["persons_created"] += 1
                        else:
                            stats["persons_updated"] += 1

                        # Prepare task activity
                        task_activities.append({
                            "person_id": person.id,
                            "notion_task_id": page_id,
                            "task_title": title,
                            "project_name": project_name,
                            "completed_at": completed_at,
                            "last_status_change": last_edited_time,
                            "notion_metadata": {
                                "notion_url": page.get("url"),
                                "status": status_name,
                                "properties": properties
                            }
                        })

                except Exception as e:
                    error_msg = f"Error processing task {page.get('id')}: {str(e)}"
                    logger.error("task_processing_error", error=error_msg)
                    stats["errors"].append(error_msg)

            # Bulk create tasks
            if task_activities:
                created = await self.activity_repo.bulk_create_tasks(task_activities)
                stats["synced"] = len(created)

        except Exception as e:
            error_msg = f"Error syncing tasks: {str(e)}"
            logger.error("sync_tasks_failed", error=error_msg)
            stats["errors"].append(error_msg)

        return stats

    def _extract_title(self, properties: Dict) -> str:
        """Extract title from Notion properties."""
        # Try common title property names
        for prop_name in ["Meeting name", "Name", "Task name", "Название бага или предложение по улучшению", "Title"]:
            if prop_name in properties:
                title_prop = properties[prop_name]
                if title_prop.get("type") == "title" and title_prop.get("title"):
                    title = "".join([t.get("plain_text", "") for t in title_prop["title"]])
                    if title.strip():  # Only return if not empty
                        return title

        return "Untitled"

    def _extract_project(self, properties: Dict) -> Optional[str]:
        """Extract project name from Notion properties."""
        for prop_name in ["Project Name", "Epic", "Project", "Project name"]:
            if prop_name in properties:
                prop = properties[prop_name]
                
                # Handle multi_select (e.g., "Project Name" in Kanban)
                if prop.get("type") == "multi_select" and prop.get("multi_select"):
                    names = [item.get("name", "") for item in prop["multi_select"]]
                    if names:
                        return ", ".join(names)
                
                # Handle rich_text
                if prop.get("rich_text"):
                    text = "".join([t.get("plain_text", "") for t in prop["rich_text"]])
                    if text.strip():
                        return text
                
                # Handle select
                if prop.get("select") and prop["select"]:
                    return prop["select"].get("name")
                
                # Handle relation (just note it exists, can't get name without extra API call)
                if prop.get("type") == "relation" and prop.get("relation"):
                    if len(prop["relation"]) > 0:
                        return "[Related Project]"

        return None

    def _extract_people(self, properties: Dict) -> List[Dict]:
        """Extract people from Notion properties."""
        people = []

        # Try common people property names (Attendees for conversations, Person for tasks)
        for prop_name in ["Attendees", "Person", "Assigned To", "Assignee", "Assign"]:
            if prop_name in properties:
                prop = properties[prop_name]
                if prop.get("type") == "people" and prop.get("people"):
                    for person in prop["people"]:
                        people.append({
                            "id": person.get("id"),
                            "name": person.get("name", "Unknown"),
                            "avatar_url": person.get("avatar_url")
                        })
                    break

        return people

    def _parse_attendee_from_title(self, title: str) -> Optional[str]:
        """
        Parse attendee name from conversation title.
        
        Expected format: "Name - Description" or "Name: Description"
        Examples:
            "Тамирлан - Обсуждение..." -> "Тамирлан"
            "Adilov Amir - Weekly sync" -> "Adilov Amir"
            "User - Daily standup" -> "User"
        
        Returns:
            Attendee name if found, None otherwise
        """
        if not title:
            return None
        
        # Try to split by " - " or " : "
        for separator in [" - ", ": ", " — "]:
            if separator in title:
                parts = title.split(separator, 1)
                if len(parts) >= 1:
                    attendee_name = parts[0].strip()
                    # Make sure it's not too long (likely not a name if > 50 chars)
                    if attendee_name and len(attendee_name) < 50:
                        return attendee_name
        
        return None

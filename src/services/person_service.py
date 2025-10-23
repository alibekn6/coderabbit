"""
Person service for business logic.

This service handles business logic for Person management.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.person_repository import PersonRepository
from src.repositories.activity_repository import ActivityRepository
from src.models.person import (
    PersonCreate,
    PersonUpdate,
    PersonResponse,
    PersonWithStats,
    PersonListResponse,
    PersonStatsListResponse
)
from src.core.logging import get_logger

logger = get_logger(__name__)


class PersonService:
    """Service for Person-related business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.person_repo = PersonRepository(session)
        self.activity_repo = ActivityRepository(session)

    async def create_person(self, data: PersonCreate) -> PersonResponse:
        """
        Create a new person.

        Args:
            data: Person creation data

        Returns:
            Created person response
        """
        # Check if person already exists
        existing = await self.person_repo.get_by_notion_id(data.notion_id)
        if existing:
            logger.warning("person_already_exists", notion_id=data.notion_id)
            raise ValueError(f"Person with Notion ID {data.notion_id} already exists")

        if data.email:
            existing_email = await self.person_repo.get_by_email(data.email)
            if existing_email:
                raise ValueError(f"Person with email {data.email} already exists")

        if data.telegram_id:
            existing_tg = await self.person_repo.get_by_telegram_id(data.telegram_id)
            if existing_tg:
                raise ValueError(
                    f"Person with Telegram ID {data.telegram_id} already exists"
                )

        person = await self.person_repo.create(
            notion_id=data.notion_id,
            username=data.username,
            avatar_url=data.avatar_url,
            email=data.email,
            telegram_id=data.telegram_id
        )

        await self.session.commit()

        return PersonResponse.model_validate(person)

    async def get_person(self, person_id: int) -> Optional[PersonResponse]:
        """
        Get a person by ID.

        Args:
            person_id: Person ID

        Returns:
            Person response or None if not found
        """
        person = await self.person_repo.get_by_id(person_id)
        if not person:
            return None

        return PersonResponse.model_validate(person)

    async def get_person_by_notion_id(
        self, notion_id: str
    ) -> Optional[PersonResponse]:
        """
        Get a person by Notion ID.

        Args:
            notion_id: Notion user ID

        Returns:
            Person response or None if not found
        """
        person = await self.person_repo.get_by_notion_id(notion_id)
        if not person:
            return None

        return PersonResponse.model_validate(person)

    async def get_person_with_stats(
        self, person_id: int
    ) -> Optional[PersonWithStats]:
        """
        Get a person with activity statistics.

        Args:
            person_id: Person ID

        Returns:
            Person with stats or None if not found
        """
        person = await self.person_repo.get_by_id(person_id)
        if not person:
            return None

        # Get activity counts
        activities, _ = await self.activity_repo.get_person_activities(
            person_id=person_id
        )

        # Count by type
        total_conversations = sum(
            1 for a in activities if a["activity_type"] == "conversation"
        )
        total_tasks = sum(1 for a in activities if a["activity_type"] == "task")

        # Calculate streak
        streak_info = await self.activity_repo.calculate_streak(person_id)

        # Calculate total activity score from summaries
        from src.schemas.person import ActivitySummary
        from sqlalchemy import select, func

        result = await self.session.execute(
            select(func.sum(ActivitySummary.total_activity_score)).where(
                ActivitySummary.person_id == person_id
            )
        )
        total_score = result.scalar_one() or 0

        return PersonWithStats(
            id=person.id,
            notion_id=person.notion_id,
            username=person.username,
            email=person.email,
            telegram_id=person.telegram_id,
            created_at=person.created_at,
            updated_at=person.updated_at,
            total_conversations=total_conversations,
            total_tasks_completed=total_tasks,
            total_activity_score=int(total_score),
            current_streak=streak_info["current_streak"],
            longest_streak=streak_info["longest_streak"]
        )

    async def list_persons(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        with_stats: bool = False
    ):
        """
        List all persons with optional pagination and search.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Search term for name or email
            with_stats: Include activity statistics

        Returns:
            List of persons (with or without stats)
        """
        persons, total = await self.person_repo.get_all(
            skip=skip, limit=limit, search=search
        )

        if not with_stats:
            persons_list = [PersonResponse.model_validate(p) for p in persons]
            return PersonListResponse(total=total, persons=persons_list)

        # Get persons with stats
        persons_with_stats = []
        for person in persons:
            person_stats = await self.get_person_with_stats(person.id)
            if person_stats:
                persons_with_stats.append(person_stats)

        return PersonStatsListResponse(total=total, persons=persons_with_stats)

    async def update_person(
        self, person_id: int, data: PersonUpdate
    ) -> Optional[PersonResponse]:
        """
        Update a person's information.

        Args:
            person_id: Person ID
            data: Update data

        Returns:
            Updated person response or None if not found
        """
        # Check uniqueness constraints
        if data.email:
            existing = await self.person_repo.get_by_email(data.email)
            if existing and existing.id != person_id:
                raise ValueError(f"Email {data.email} is already in use")

        if data.telegram_id:
            existing = await self.person_repo.get_by_telegram_id(data.telegram_id)
            if existing and existing.id != person_id:
                raise ValueError(f"Telegram ID {data.telegram_id} is already in use")

        person = await self.person_repo.update(
            person_id=person_id,
            username=data.username,
            avatar_url=data.avatar_url,
            email=data.email,
            telegram_id=data.telegram_id
        )

        if not person:
            return None

        await self.session.commit()

        return PersonResponse.model_validate(person)

    async def delete_person(self, person_id: int) -> bool:
        """
        Delete a person.

        Args:
            person_id: Person ID

        Returns:
            True if deleted, False if not found
        """
        deleted = await self.person_repo.delete(person_id)
        if deleted:
            await self.session.commit()

        return deleted

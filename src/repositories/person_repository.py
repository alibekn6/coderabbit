"""
Person repository for database operations.

This repository handles CRUD operations for Person entities.
"""

from typing import Optional, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.person import Person
from src.core.logging import get_logger

logger = get_logger(__name__)


class PersonRepository:
    """Repository for Person-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        notion_id: str,
        username: str,
        avatar_url: Optional[str] = None,
        email: Optional[str] = None,
        telegram_id: Optional[str] = None
    ) -> Person:
        """
        Create a new person.

        Args:
            notion_id: Notion user ID
            username: Username
            avatar_url: Avatar URL (optional)
            email: Email address (optional)
            telegram_id: Telegram user ID (optional)

        Returns:
            Created Person object
        """
        person = Person(
            notion_id=notion_id,
            username=username,
            avatar_url=avatar_url,
            email=email,
            telegram_id=telegram_id
        )

        self.session.add(person)
        await self.session.flush()
        await self.session.refresh(person)

        logger.info("person_created", person_id=person.id, notion_id=notion_id, username=username)
        return person

    async def get_by_id(self, person_id: int) -> Optional[Person]:
        """
        Get a person by ID.

        Args:
            person_id: Person ID

        Returns:
            Person object or None if not found
        """
        result = await self.session.execute(
            select(Person).where(Person.id == person_id)
        )
        return result.scalar_one_or_none()

    async def get_by_notion_id(self, notion_id: str) -> Optional[Person]:
        """
        Get a person by Notion ID.

        Args:
            notion_id: Notion user ID

        Returns:
            Person object or None if not found
        """
        result = await self.session.execute(
            select(Person).where(Person.notion_id == notion_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Person]:
        """
        Get a person by email.

        Args:
            email: Email address

        Returns:
            Person object or None if not found
        """
        result = await self.session.execute(
            select(Person).where(Person.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: str) -> Optional[Person]:
        """
        Get a person by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Person object or None if not found
        """
        result = await self.session.execute(
            select(Person).where(Person.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> tuple[List[Person], int]:
        """
        Get all persons with optional pagination and search.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Search term for name or email

        Returns:
            Tuple of (list of Person objects, total count)
        """
        query = select(Person)

        # Apply search filter if provided
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Person.username.ilike(search_pattern),
                    Person.email.ilike(search_pattern)
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(Person.username)

        result = await self.session.execute(query)
        persons = result.scalars().all()

        return list(persons), total

    async def update(
        self,
        person_id: int,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        email: Optional[str] = None,
        telegram_id: Optional[str] = None
    ) -> Optional[Person]:
        """
        Update a person's information.

        Args:
            person_id: Person ID
            username: New username (optional)
            avatar_url: New avatar URL (optional)
            email: New email (optional)
            telegram_id: New Telegram ID (optional)

        Returns:
            Updated Person object or None if not found
        """
        person = await self.get_by_id(person_id)
        if not person:
            return None

        if username is not None:
            person.username = username
        if avatar_url is not None:
            person.avatar_url = avatar_url
        if email is not None:
            person.email = email
        if telegram_id is not None:
            person.telegram_id = telegram_id

        await self.session.flush()
        await self.session.refresh(person)

        logger.info("person_updated", person_id=person_id)
        return person

    async def delete(self, person_id: int) -> bool:
        """
        Delete a person.

        Args:
            person_id: Person ID

        Returns:
            True if deleted, False if not found
        """
        person = await self.get_by_id(person_id)
        if not person:
            return False

        await self.session.delete(person)
        await self.session.flush()

        logger.info("person_deleted", person_id=person_id)
        return True

    async def get_or_create_by_notion_id(
        self,
        notion_id: str,
        username: str,
        avatar_url: Optional[str] = None,
        email: Optional[str] = None
    ) -> tuple[Person, bool]:
        """
        Get an existing person by Notion ID or create a new one.

        Args:
            notion_id: Notion user ID
            username: Username
            avatar_url: Avatar URL (optional)
            email: Email address (optional)

        Returns:
            Tuple of (Person object, created flag)
        """
        person = await self.get_by_notion_id(notion_id)
        if person:
            # Update username and avatar if changed
            if person.username != username or person.avatar_url != avatar_url:
                person.username = username
                person.avatar_url = avatar_url
                await self.session.flush()
                await self.session.refresh(person)
            return person, False

        # Create new person
        person = await self.create(
            notion_id=notion_id,
            username=username,
            avatar_url=avatar_url,
            email=email
        )
        return person, True

    async def bulk_get_or_create(
        self,
        persons_data: List[dict]
    ) -> List[tuple[Person, bool]]:
        """
        Bulk get or create persons.

        Args:
            persons_data: List of dicts with keys: notion_id, username, avatar_url (optional), email (optional)

        Returns:
            List of tuples (Person object, created flag)
        """
        results = []
        for data in persons_data:
            person, created = await self.get_or_create_by_notion_id(
                notion_id=data["notion_id"],
                username=data["username"],
                avatar_url=data.get("avatar_url"),
                email=data.get("email")
            )
            results.append((person, created))

        return results

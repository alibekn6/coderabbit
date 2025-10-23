"""
Authentication repository for database operations.

This repository handles database queries related to authentication.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.user import User, RefreshToken


class AuthRepository:
    """Repository for authentication-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.

        Args:
            username: Username to search for

        Returns:
            User object or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email.

        Args:
            email: Email to search for

        Returns:
            User object or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create_user(self, username: str, email: str, hashed_password: str) -> User:
        """
        Create a new user in the database.

        Args:
            username: User's username
            email: User's email
            hashed_password: Bcrypt hashed password

        Returns:
            Created User object
        """
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=True
        )

        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def create_refresh_token(
        self,
        user_id: int,
        token: str,
        expires_days: int,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> RefreshToken:
        """
        Create a new refresh token in the database.

        Args:
            user_id: ID of the user
            token: Refresh token string
            expires_days: Number of days until expiration
            user_agent: User agent string from request
            ip_address: IP address from request

        Returns:
            Created RefreshToken object
        """
        refresh_token = RefreshToken(
            token=token,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
            user_agent=user_agent,
            ip_address=ip_address,
            is_revoked=False
        )

        self.session.add(refresh_token)
        await self.session.flush()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """
        Get a refresh token by token string.

        Args:
            token: Refresh token string

        Returns:
            RefreshToken object or None if not found
        """
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token_id: int) -> None:
        """
        Revoke a refresh token by marking it as revoked.

        Args:
            token_id: ID of the refresh token to revoke
        """
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.id == token_id)
        )
        refresh_token = result.scalar_one_or_none()

        if refresh_token:
            refresh_token.is_revoked = True
            await self.session.flush()

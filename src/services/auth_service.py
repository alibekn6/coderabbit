"""
Authentication service layer for business logic.

This service handles authentication-related operations including registration,
login, and token management.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.core.logging import get_logger
from src.core.security import hash_password, verify_password, create_access_token, generate_refresh_token
from src.core.config import Config
from src.models.auth import UserRegister, UserLogin, TokenResponse, UserResponse
from src.repositories.auth_repository import AuthRepository
from src.schemas.user import User

logger = get_logger(__name__)
config = Config()


class AuthService:
    """Service for managing authentication-related business logic."""

    def __init__(self, auth_repository: AuthRepository):
        self.auth_repository = auth_repository

    async def register_user(
        self,
        user_data: UserRegister,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> TokenResponse:
        """
        Register a new user and return authentication tokens.

        Args:
            user_data: User registration data
            user_agent: User agent from request headers
            ip_address: IP address from request

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            ValueError: If username or email already exists

        Example:
            >>> service = AuthService(auth_repository)
            >>> tokens = await service.register_user(user_data)
        """
        logger.info(
            "registering_user",
            username=user_data.username,
            email=user_data.email
        )

        # Check if username already exists
        existing_user = await self.auth_repository.get_user_by_username(user_data.username)
        if existing_user:
            logger.warning(
                "registration_failed_username_exists",
                username=user_data.username
            )
            raise ValueError("Username already exists")

        # Check if email already exists
        existing_email = await self.auth_repository.get_user_by_email(user_data.email)
        if existing_email:
            logger.warning(
                "registration_failed_email_exists",
                email=user_data.email
            )
            raise ValueError("Email already exists")

        try:
            # Hash the password
            hashed_password = hash_password(user_data.password)

            # Create the user
            user = await self.auth_repository.create_user(
                username=user_data.username,
                email=user_data.email,
                hashed_password=hashed_password
            )

            # Generate tokens
            access_token = create_access_token(
                data={"sub": str(user.id), "username": user.username}
            )
            refresh_token = generate_refresh_token()

            # Store refresh token
            await self.auth_repository.create_refresh_token(
                user_id=user.id,
                token=refresh_token,
                expires_days=config.REFRESH_TOKEN_EXPIRE_DAYS,
                user_agent=user_agent,
                ip_address=ip_address
            )

            logger.info(
                "user_registered_successfully",
                user_id=user.id,
                username=user.username,
                email=user.email
            )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token
            )

        except Exception as e:
            logger.error(
                "user_registration_failed",
                username=user_data.username,
                email=user_data.email,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise

    async def login_user(
        self,
        login_data: UserLogin,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> TokenResponse:
        """
        Authenticate a user and return authentication tokens.

        Args:
            login_data: User login credentials (username, password)
            user_agent: User agent from request headers
            ip_address: IP address from request

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            ValueError: If credentials are invalid or user is inactive

        Example:
            >>> service = AuthService(auth_repository)
            >>> tokens = await service.login_user(login_data)
        """
        logger.info(
            "login_attempt",
            username=login_data.username,
            ip_address=ip_address
        )

        # Get user by username
        user = await self.auth_repository.get_user_by_username(login_data.username)

        if not user:
            logger.warning(
                "login_failed_user_not_found",
                username=login_data.username,
                ip_address=ip_address
            )
            raise ValueError("Invalid username or password")

        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            logger.warning(
                "login_failed_invalid_password",
                username=login_data.username,
                user_id=user.id,
                ip_address=ip_address
            )
            raise ValueError("Invalid username or password")

        # Check if user is active
        if not user.is_active:
            logger.warning(
                "login_failed_user_inactive",
                username=login_data.username,
                user_id=user.id,
                ip_address=ip_address
            )
            raise ValueError("Account is inactive")

        try:
            # Generate tokens
            access_token = create_access_token(
                data={"sub": str(user.id), "username": user.username}
            )
            refresh_token = generate_refresh_token()

            # Store refresh token
            await self.auth_repository.create_refresh_token(
                user_id=user.id,
                token=refresh_token,
                expires_days=config.REFRESH_TOKEN_EXPIRE_DAYS,
                user_agent=user_agent,
                ip_address=ip_address
            )

            logger.info(
                "login_successful",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address
            )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token
            )

        except Exception as e:
            logger.error(
                "login_failed",
                username=login_data.username,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise

    async def refresh_access_token(
        self,
        refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> TokenResponse:
        """
        Refresh access token using a valid refresh token.

        This method follows the security best practice of rotating refresh tokens:
        - Validates the provided refresh token
        - Generates new access and refresh tokens
        - Revokes the old refresh token
        - Stores the new refresh token

        Args:
            refresh_token: The refresh token string
            user_agent: User agent from request headers
            ip_address: IP address from request

        Returns:
            TokenResponse with new access and refresh tokens

        Raises:
            ValueError: If token is invalid, expired, revoked, or user is inactive

        Example:
            >>> service = AuthService(auth_repository)
            >>> tokens = await service.refresh_access_token(refresh_token)
        """
        logger.info(
            "refresh_token_request",
            ip_address=ip_address
        )

        # Get refresh token from database
        db_refresh_token = await self.auth_repository.get_refresh_token(refresh_token)

        if not db_refresh_token:
            logger.warning(
                "refresh_token_not_found",
                ip_address=ip_address
            )
            raise ValueError("Invalid refresh token")

        # Check if token is revoked
        if db_refresh_token.is_revoked:
            logger.warning(
                "refresh_token_revoked",
                token_id=db_refresh_token.id,
                user_id=db_refresh_token.user_id,
                ip_address=ip_address
            )
            raise ValueError("Refresh token has been revoked")

        # Check if token is expired
        if db_refresh_token.expires_at < datetime.now(timezone.utc):
            logger.warning(
                "refresh_token_expired",
                token_id=db_refresh_token.id,
                user_id=db_refresh_token.user_id,
                expires_at=db_refresh_token.expires_at,
                ip_address=ip_address
            )
            raise ValueError("Refresh token has expired")

        # Get the user
        user = await self.auth_repository.get_user_by_id(db_refresh_token.user_id)

        if not user:
            logger.error(
                "refresh_token_user_not_found",
                token_id=db_refresh_token.id,
                user_id=db_refresh_token.user_id
            )
            raise ValueError("User not found")

        # Check if user is active
        if not user.is_active:
            logger.warning(
                "refresh_token_user_inactive",
                token_id=db_refresh_token.id,
                user_id=user.id,
                username=user.username,
                ip_address=ip_address
            )
            raise ValueError("User account is inactive")

        try:
            # Generate new tokens
            new_access_token = create_access_token(
                data={"sub": str(user.id), "username": user.username}
            )
            new_refresh_token = generate_refresh_token()

            # Store new refresh token
            await self.auth_repository.create_refresh_token(
                user_id=user.id,
                token=new_refresh_token,
                expires_days=config.REFRESH_TOKEN_EXPIRE_DAYS,
                user_agent=user_agent,
                ip_address=ip_address
            )

            # Revoke old refresh token (security best practice)
            await self.auth_repository.revoke_refresh_token(db_refresh_token.id)

            logger.info(
                "refresh_token_successful",
                user_id=user.id,
                username=user.username,
                old_token_id=db_refresh_token.id,
                ip_address=ip_address
            )

            return TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token
            )

        except Exception as e:
            logger.error(
                "refresh_token_failed",
                user_id=user.id if user else None,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise

    def get_user_response(self, user: User) -> UserResponse:
        """
        Convert a User database model to UserResponse.

        Args:
            user: User database model

        Returns:
            UserResponse with user information

        Example:
            >>> service = AuthService(auth_repository)
            >>> user_response = service.get_user_response(user)
        """
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active
        )

"""
Google Sheets OAuth Authentication Service
Handles user authentication and token management for Google Sheets access
"""

import httpx
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.config import settings
from app.models.sheet_sync import UserSheetsToken

logger = structlog.get_logger()

# Google OAuth Scopes
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


class GoogleSheetsAuth:
    """
    Manages Google OAuth authentication for Sheets access
    - Generates OAuth URLs
    - Exchanges auth code for tokens
    - Refreshes expired tokens
    - Validates token status
    """

    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.scopes = SHEETS_SCOPES

    def get_google_oauth_url(self, state: str) -> str:
        """
        Generate Google OAuth authorization URL
        
        Args:
            state: CSRF protection state token
            
        Returns:
            OAuth URL for user to click
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",  # Force consent to get refresh token
            "state": state,
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self.auth_url}?{query_string}"

        logger.info("oauth_url_generated", state=state)
        return url

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access/refresh tokens
        
        Args:
            code: Authorization code from Google
            
        Returns:
            {
                "access_token": "...",
                "refresh_token": "...",
                "expires_in": 3600,
                "token_type": "Bearer"
            }
        """
        try:
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.token_url, data=payload, timeout=10)
                response.raise_for_status()
                tokens = response.json()

            logger.info("oauth_tokens_exchanged")
            return tokens

        except httpx.HTTPError as e:
            logger.error("oauth_exchange_failed", error=str(e))
            raise Exception(f"Failed to exchange OAuth code: {str(e)}")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh expired access token using refresh token
        
        Args:
            refresh_token: Refresh token from previous auth
            
        Returns:
            {
                "access_token": "...",
                "expires_in": 3600,
                "token_type": "Bearer"
            }
        """
        try:
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.token_url, data=payload, timeout=10)
                response.raise_for_status()
                tokens = response.json()

            logger.info("oauth_token_refreshed")
            return tokens

        except httpx.HTTPError as e:
            logger.error("oauth_refresh_failed", error=str(e))
            raise Exception(f"Failed to refresh OAuth token: {str(e)}")

    async def save_user_tokens(
        self,
        db: AsyncSession,
        user_id: str,
        user_email: str,
        access_token: str,
        refresh_token: Optional[str],
        expires_in: int,
    ) -> UserSheetsToken:
        """
        Save or update user's Google tokens in database
        
        Args:
            db: Database session
            user_id: Google OAuth user ID
            user_email: User email
            access_token: Google API access token
            refresh_token: Refresh token (if available)
            expires_in: Token expiry time in seconds
            
        Returns:
            UserSheetsToken model instance
        """
        try:
            # Check if user already exists
            stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
            result = await db.execute(stmt)
            existing_token = result.scalars().first()

            token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            if existing_token:
                # Update existing
                stmt = (
                    update(UserSheetsToken)
                    .where(UserSheetsToken.user_id == user_id)
                    .values(
                        user_email=user_email,
                        access_token=access_token,
                        refresh_token=refresh_token or existing_token.refresh_token,
                        token_expires_at=token_expires_at,
                        is_active=True,
                        last_used_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                await db.execute(stmt)
                await db.commit()

                logger.info("user_tokens_updated", user_id=user_id)
                return await db.execute(
                    select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
                )

            else:
                # Create new
                token = UserSheetsToken(
                    user_id=user_id,
                    user_email=user_email,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expires_at=token_expires_at,
                    is_active=True,
                    last_used_at=datetime.utcnow(),
                )
                db.add(token)
                await db.commit()
                await db.refresh(token)

                logger.info("user_tokens_created", user_id=user_id)
                return token

        except Exception as e:
            logger.error("save_user_tokens_failed", user_id=user_id, error=str(e))
            await db.rollback()
            raise

    async def get_valid_token(
        self, db: AsyncSession, user_id: str
    ) -> Optional[str]:
        """
        Get valid access token for user, refresh if expired
        
        Args:
            db: Database session
            user_id: Google OAuth user ID
            
        Returns:
            Valid access token or None if not found
        """
        try:
            stmt = select(UserSheetsToken).where(UserSheetsToken.user_id == user_id)
            result = await db.execute(stmt)
            token_record = result.scalars().first()

            if not token_record or not token_record.is_active:
                logger.warning("user_token_not_found", user_id=user_id)
                return None

            # Check if token expired
            if datetime.utcnow() >= token_record.token_expires_at:
                # Try to refresh
                if token_record.refresh_token:
                    logger.info("token_expired_refreshing", user_id=user_id)

                    new_tokens = await self.refresh_access_token(
                        token_record.refresh_token
                    )

                    # Update in database
                    await self.save_user_tokens(
                        db,
                        user_id,
                        token_record.user_email,
                        new_tokens["access_token"],
                        token_record.refresh_token,
                        new_tokens["expires_in"],
                    )

                    return new_tokens["access_token"]
                else:
                    logger.warning(
                        "token_expired_no_refresh_token", user_id=user_id
                    )
                    return None

            # Update last_used_at
            stmt = (
                update(UserSheetsToken)
                .where(UserSheetsToken.user_id == user_id)
                .values(last_used_at=datetime.utcnow())
            )
            await db.execute(stmt)
            await db.commit()

            return token_record.access_token

        except Exception as e:
            logger.error("get_valid_token_failed", user_id=user_id, error=str(e))
            return None

    async def revoke_token(self, db: AsyncSession, user_id: str) -> bool:
        """
        Revoke user's Google tokens
        
        Args:
            db: Database session
            user_id: Google OAuth user ID
            
        Returns:
            Success status
        """
        try:
            stmt = (
                update(UserSheetsToken)
                .where(UserSheetsToken.user_id == user_id)
                .values(is_active=False)
            )
            await db.execute(stmt)
            await db.commit()

            logger.info("user_tokens_revoked", user_id=user_id)
            return True

        except Exception as e:
            logger.error("revoke_token_failed", user_id=user_id, error=str(e))
            return False

    async def validate_token_access(self, access_token: str) -> bool:
        """
        Validate if access token is still valid
        
        Args:
            access_token: Google API access token
            
        Returns:
            True if valid, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v1/tokeninfo",
                    params={"access_token": access_token},
                    timeout=10,
                )

                return response.status_code == 200

        except Exception as e:
            logger.error("validate_token_access_failed", error=str(e))
            return False

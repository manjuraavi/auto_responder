# app/auth/gmail_auth.py
"""
Gmail OAuth2 Authentication Service
Handles Google OAuth2 flow for Gmail API access
"""

import json
import os
from typing import Optional, Dict, Any
from urllib.parse import urlencode
import secrets
import logging
from datetime import datetime, timedelta
import jwt
from fastapi import Cookie, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import aiohttp

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# Fix: Use requests_oauthlib instead of google_auth_oauthlib.oauth2session
from requests_oauthlib import OAuth2Session

from app.config.settings import settings
from app.utils.exceptions import AuthenticationError, AuthenticationException
from app.utils.logging_config import get_logger

logger = logging.getLogger(__name__)
security = HTTPBearer()


class GmailAuthService:
    """
    Gmail OAuth2 authentication service.
    Handles the complete OAuth2 flow for Gmail API access.
    """
    
    def __init__(self):
        self.client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
            }
        }
        self.scopes = settings.GMAIL_SCOPES
        
    def get_authorization_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate authorization URL for Gmail OAuth2 flow.
        
        Args:
            state: Optional state parameter for security
            
        Returns:
            Tuple of (authorization_url, state)
            
        Raises:
            AuthenticationError: If URL generation fails
        """
        try:
            # Generate secure state if not provided
            if not state:
                state = secrets.token_urlsafe(32)
            
            # Create OAuth2 flow
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                state=state
            )
            flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
            
            # Generate authorization URL
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            logger.info(f"Generated authorization URL with state: {state}")
            return authorization_url, state
            
        except Exception as e:
            logger.error(f"Failed to generate authorization URL: {e}")
            raise AuthenticationError(f"Failed to generate authorization URL: {str(e)}")
    
    def exchange_code_for_tokens(self, code: str, state: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth2 callback
            state: State parameter for verification
            
        Returns:
            Dictionary containing token information and user details
            
        Raises:
            AuthenticationError: If token exchange fails
        """
        try:
            # Create OAuth2 flow
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                state=state
            )
            flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
            
            # Exchange code for tokens
            flow.fetch_token(code=code)
            
            # Get credentials
            credentials = flow.credentials
            
            # Get user information
            user_info = self._get_user_info(credentials)
            
            # Prepare token response
            token_data = {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_in": credentials.expiry.timestamp() if credentials.expiry else None,
                "scope": " ".join(self.scopes),
                "token_type": "Bearer",
                "user_info": user_info
            }
            
            logger.info(f"Successfully exchanged code for tokens: {user_info.get('email')}")
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            raise AuthenticationError(f"Failed to exchange authorization code: {str(e)}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary containing new token information
            
        Raises:
            AuthenticationError: If token refresh fails
        """
        try:
            # Create credentials from refresh token
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=self.scopes
            )
            
            # Refresh the token
            credentials.refresh(Request())
            
            # Prepare response
            token_data = {
                "access_token": credentials.token,
                "expires_in": credentials.expiry.timestamp() if credentials.expiry else None,
                "token_type": "Bearer"
            }
            
            logger.info("Successfully refreshed access token")
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise AuthenticationError(f"Failed to refresh access token: {str(e)}")
    
    def validate_credentials(self, access_token: str) -> Dict[str, Any]:
        """
        Validate access token and get user information.
        
        Args:
            access_token: Access token to validate
            
        Returns:
            Dictionary containing user information
            
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Create credentials
            credentials = Credentials(token=access_token)
            
            # Get user information to validate token
            user_info = self._get_user_info(credentials)
            
            logger.info(f"Validated credentials for user: {user_info.get('email')}")
            return user_info
            
        except Exception as e:
            logger.error(f"Failed to validate credentials: {e}")
            raise AuthenticationError(f"Invalid access token: {str(e)}")
    
    def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """
        Get user information from Google API.
        
        Args:
            credentials: Google OAuth2 credentials
            
        Returns:
            Dictionary containing user information
            
        Raises:
            AuthenticationError: If user info retrieval fails
        """
        try:
            # Build service
            service = build('oauth2', 'v2', credentials=credentials)
            
            # Get user info
            user_info = service.userinfo().get().execute()
            
            return {
                "id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "verified_email": user_info.get("verified_email", False)
            }
            
        except HttpError as e:
            logger.error(f"Failed to get user info: {e}")
            raise AuthenticationError(f"Failed to get user information: {str(e)}")
    
    def revoke_credentials(self, access_token: str) -> bool:
        """
        Revoke access token.
        
        Args:
            access_token: Access token to revoke
            
        Returns:
            True if revocation successful
            
        Raises:
            AuthenticationError: If revocation fails
        """
        try:
            credentials = Credentials(token=access_token)
            credentials.revoke(Request())
            
            logger.info("Successfully revoked credentials")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            raise AuthenticationError(f"Failed to revoke credentials: {str(e)}")

    @classmethod
    def create_authorization_url(cls, scopes: list, redirect_uri: str) -> str:
        """Create Google OAuth2 authorization URL"""
        try:
            print(f"\nCreating authorization URL...")
            print(f"Redirect URI: {redirect_uri}")
            print(f"Client ID: {settings.GOOGLE_CLIENT_ID[:10]}...")
            
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri]  # Add the redirect URI here
                    }
                },
                scopes=scopes
            )
            flow.redirect_uri = redirect_uri
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            print(f"Generated auth URL: {auth_url[:100]}...")
            return auth_url
        except Exception as e:
            logger.error(f"Failed to create authorization URL: {str(e)}")
            print(f"Auth URL creation error: {str(e)}")
            raise AuthenticationException(f"Failed to create authorization URL: {str(e)}")

    @classmethod
    async def exchange_code_for_tokens(cls, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        try:
            print(f"\nExchanging code for tokens...")
            print(f"Code: {code[:10]}...")
            print(f"Redirect URI: {redirect_uri}")
            print(f"Client ID: {settings.GOOGLE_CLIENT_ID[:10]}...")
            
            # Fixed: Use requests_oauthlib.OAuth2Session
            oauth = OAuth2Session(
                client_id=settings.GOOGLE_CLIENT_ID,
                redirect_uri=redirect_uri,
                scope=settings.GMAIL_SCOPES
            )
            
            print("OAuth session created, fetching token...")
            
            # Fetch token
            token = oauth.fetch_token(
                'https://oauth2.googleapis.com/token',
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                code=code
            )
            
            print(f"Access token received: {token.get('access_token', '')[:10]}...")
            print(f"Refresh token received: {'Yes' if 'refresh_token' in token else 'No'}")
            
            # Try to get user info using the session
            try:
                user_response = oauth.get('https://www.googleapis.com/oauth2/v2/userinfo')
                if user_response.status_code == 200:
                    user_info = user_response.json()
                    print(f"User info fetched successfully for: {user_info.get('email')}")
                else:
                    print(f"Failed to get user info: {user_response.status_code}")
                    user_info = None
            except Exception as e:
                print(f"Failed to get user info: {str(e)}")
                user_info = None
            
            # Return token info
            token_info = {
                "token": token['access_token'],
                "refresh_token": token.get('refresh_token'),
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "scopes": settings.GMAIL_SCOPES,
                "expires_at": token.get('expires_at'),
                "token_type": token.get('token_type', 'Bearer')
            }
            
            # Add user info if available
            if user_info:
                token_info["user_info"] = {
                    "email": user_info["email"],
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture")
                }
            
            return token_info
            
        except Exception as e:
            logger.error(f"Failed to exchange code for tokens: {str(e)}")
            print(f"Token exchange error: {str(e)}")
            raise AuthenticationException(f"Failed to exchange code for tokens: {str(e)}")

    @classmethod
    async def get_user_info(cls, token_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get user information from Google"""
        # If user info was already fetched during token exchange, return it
        if "user_info" in token_info:
            return token_info["user_info"]
            
        try:
            # Fixed: Use requests_oauthlib.OAuth2Session
            from oauthlib.oauth2 import TokenExpiredError
            
            # Create session with existing token
            oauth = OAuth2Session(
                client_id=settings.GOOGLE_CLIENT_ID,
                token={
                    'access_token': token_info['token'],
                    'refresh_token': token_info.get('refresh_token'),
                    'token_type': token_info.get('token_type', 'Bearer'),
                    'expires_at': token_info.get('expires_at')
                }
            )
            
            try:
                # Try to get user info
                response = oauth.get('https://www.googleapis.com/oauth2/v2/userinfo')
                response.raise_for_status()
                user_info = response.json()
                
                return {
                    "email": user_info["email"],
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture")
                }
            except TokenExpiredError:
                # Token expired, try to refresh
                token = oauth.refresh_token(
                    "https://oauth2.googleapis.com/token",
                    client_id=settings.GOOGLE_CLIENT_ID,
                    client_secret=settings.GOOGLE_CLIENT_SECRET
                )
                
                # Retry with new token
                response = oauth.get('https://www.googleapis.com/oauth2/v2/userinfo')
                response.raise_for_status()
                user_info = response.json()
                
                return {
                    "email": user_info["email"],
                    "name": user_info.get("name"),
                    "picture": user_info.get("picture")
                }
                
        except Exception as e:
            logger.error(f"Failed to get user info: {str(e)}")
            raise AuthenticationException(f"Failed to get user information: {str(e)}")

    @classmethod
    def create_access_token(cls, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            to_encode.update({"exp": expire})
            
            encoded_jwt = jwt.encode(
                to_encode,
                settings.SECRET_KEY,
                algorithm=settings.ALGORITHM
            )
            
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create access token: {str(e)}")
            raise AuthenticationException("Failed to create access token")

    @classmethod
    async def refresh_tokens(cls, refresh_token: str) -> Dict[str, Any]:
        """Refresh Google OAuth2 tokens"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token"
                    }
                ) as response:
                    if response.status != 200:
                        raise AuthenticationException("Failed to refresh tokens")
                    
                    data = await response.json()
                    return {
                        "token": data["access_token"],
                        "refresh_token": refresh_token,  # Keep the same refresh token
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "scopes": settings.GMAIL_SCOPES
                    }
        except Exception as e:
            logger.error(f"Failed to refresh tokens: {str(e)}")
            raise AuthenticationException("Failed to refresh tokens")

    @classmethod
    async def revoke_tokens(cls, token_info: Dict[str, Any]) -> None:
        """Revoke Google OAuth2 tokens"""
        try:
            # Revoke access token
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": token_info["token"]}
                ) as response:
                    if response.status != 200:
                        logger.warning("Failed to revoke access token")
                
                # Revoke refresh token if available
                if token_info.get("refresh_token"):
                    async with session.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": token_info["refresh_token"]}
                    ) as response:
                        if response.status != 200:
                            logger.warning("Failed to revoke refresh token")
        except Exception as e:
            logger.error(f"Failed to revoke tokens: {str(e)}")
            raise AuthenticationException("Failed to revoke tokens")

    @classmethod
    async def get_current_user(
        cls,
        access_token: str = Cookie(None)
    ) -> Dict[str, Any]:
        """Get current user from JWT token in HTTP-only cookie"""
        try:
            if not access_token:
                raise AuthenticationException("Not authenticated")
            payload = jwt.decode(
                access_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
                raise AuthenticationException("Token has expired")
            return payload
        except jwt.PyJWTError as e:
            logger.error(f"Failed to decode JWT token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        except Exception as e:
            logger.error(f"Failed to get current user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
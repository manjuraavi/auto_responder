"""
Authentication router for Google OAuth2
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional
import logging
from app.auth.gmail_auth import GmailAuthService
from app.config.settings import settings
from app.utils.exceptions import AuthenticationException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

class CallbackRequest(BaseModel):
    code: str
    redirect_uri: str

@router.post("/google")
async def google_auth():
    """Initiate Google OAuth2 flow"""
    try:
        print("\n=== Starting OAuth Flow ===")
        print(f"Settings loaded - Client ID: {settings.GOOGLE_CLIENT_ID[:10]}...")
        
        # Use root URL for redirect
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        print(f"Using redirect URI: {redirect_uri}")
        
        # Create auth URL with required scopes
        auth_url = GmailAuthService.create_authorization_url(
            scopes=settings.GMAIL_SCOPES,
            redirect_uri=redirect_uri
        )
        print(f"Generated Auth URL: {auth_url[:100]}...")
        print("=========================\n")
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Failed to create authorization URL: {str(e)}")
        print(f"\n=== OAuth Error ===")
        print(f"Error creating auth URL: {str(e)}")
        print("==================\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/google/callback")
async def google_callback(code: str):
    """Handle Google OAuth2 callback"""
    try:
        print("\n=== Processing OAuth Callback ===")
        print(f"Received code: {code[:10]}...")
        print(f"Current settings:")
        print(f"- Client ID: {settings.GOOGLE_CLIENT_ID[:10]}...")
        print(f"- Scopes: {settings.GMAIL_SCOPES}")
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        # Validate redirect URI
        if redirect_uri != settings.GOOGLE_REDIRECT_URI:
            print(f"Redirect URI mismatch: {redirect_uri} != {settings.GOOGLE_REDIRECT_URI}")
            raise AuthenticationException("Invalid redirect URI")
        
        # Exchange code for tokens
        token_info = await GmailAuthService.exchange_code_for_tokens(
            code=code,
            redirect_uri=settings.GOOGLE_REDIRECT_URI  # Use configured redirect URI
        )
        print("Successfully exchanged code for tokens")
        
        # Get user info - either from token_info or fetch separately
        if "user_info" in token_info:
            user_info = token_info.pop("user_info")
            print(f"Using user info from token exchange: {user_info.get('email')}")
        else:
            print("User info not in token response, fetching separately...")
            user_info = await GmailAuthService.get_user_info(token_info)
            print(f"Fetched user info separately: {user_info.get('email')}")
        
        # Create session token
        access_token = GmailAuthService.create_access_token(
            data={
                "sub": user_info["email"],
                "email": user_info["email"],
                "tokens": token_info
            }
        )
        print("Created session token")
        print("==============================\n")
        
        response = RedirectResponse(url=settings.FRONTEND_URL + "/dashboard")
        # Set the token as a secure, HTTP-only cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS!
            samesite="lax",
            max_age=60 * 60 * 24  # 1 day, adjust as needed
        )
        return response
    except Exception as e:
        logger.error(f"Failed to complete authentication: {str(e)}")
        print(f"\n=== OAuth Callback Error ===")
        print(f"Error during callback: {str(e)}")
        print(f"Code: {code[:10]}...")
        print(f"Redirect URI: {redirect_uri}")
        print("=========================\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.get("/me")
async def get_me(current_user: dict = Depends(GmailAuthService.get_current_user)):
    return {"user": current_user}

@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(GmailAuthService.get_current_user)):
    """Refresh Google OAuth2 tokens"""
    try:
        # Get refresh token from current user
        refresh_token = current_user["tokens"].get("refresh_token")
        if not refresh_token:
            raise AuthenticationException("No refresh token available")
        
        # Refresh tokens
        new_tokens = await GmailAuthService.refresh_tokens(refresh_token)
        
        # Create new session token
        access_token = GmailAuthService.create_access_token(
            data={
                "sub": current_user["email"],
                "email": current_user["email"],
                "tokens": new_tokens
            }
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout(current_user: dict = Depends(GmailAuthService.get_current_user)):
    """Logout user and revoke Google OAuth2 tokens"""
    try:
        # Revoke tokens
        await GmailAuthService.revoke_tokens(current_user["tokens"])
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Failed to logout: {str(e)}")
        # Even if revocation fails, we'll return success to the client
        return {"message": "Successfully logged out"}

"""
FastAPI Backend for Gmail Auto-Responder
Production-ready with real data, modular architecture, and comprehensive error handling
"""

from fastapi import Cookie, FastAPI, HTTPException, Depends, UploadFile, File, Form, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime
import os
from typing import List, Optional


# Import configuration and utilities
from app.config.settings import settings
from app.utils.exceptions import (
    CustomHTTPException,
    AuthenticationException,
    EmailServiceException,
    AIServiceException,
    VectorDBException
)
from app.utils.logging_config import setup_logging

# Import models and schemas
from app.models.schemas import (
    SystemInfo,
    HealthCheck
)

# Import authentication
from app.auth.gmail_auth import GmailAuthService

from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=".env", override=True)

# Print OAuth configuration on startup
print("\n=== OAuth Configuration ===")
print(f"Client ID: {settings.GOOGLE_CLIENT_ID}")
print(f"Redirect URI: {settings.GOOGLE_REDIRECT_URI}")
print(f"Scopes: {settings.GMAIL_SCOPES}")
print("========================\n")

# Import services
from app.services.gmail_service import GmailService
from app.services.document_service import DocumentService
from app.services.agent_service import AgentService
from app.services.vector_service import VectorService

# Import agents
from app.agents.response_generator import ResponseGeneratorAgent
from app.agents.context_retriever import ContextRetrieverAgent
from app.agents.intent_classifier import IntentClassifierAgent

# Import API routers
from app.api.auth import router as auth_router
from app.api.emails import router as email_router
from app.api.documents import router as document_router
from app.api.agents import router as agent_router
from app.api.settings_page import router as settings_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Gmail Auto-Responder API...")
    
    # Initialize services and agents
    try:
        # Initialize vector service first (required by agents)
        vector_service = VectorService()
        vector_service.initialize()  # Synchronous call
        
        # Initialize agents with vector service
        response_agent = ResponseGeneratorAgent(vector_service=vector_service)
        context_agent = ContextRetrieverAgent(vector_service=vector_service)
        intent_agent = IntentClassifierAgent(vector_service=vector_service)
        
        # Initialize agent service with agents only (user context will be added per-request)
        agent_service = AgentService(
            response_agent=response_agent,
            context_agent=context_agent,
            intent_agent=intent_agent
        )
        
        # Store services in app state
        app.state.vector_service = vector_service
        app.state.agent_service = agent_service
        
        # Verify all services
        if not await GmailService.verify_connection():
            raise EmailServiceException("Failed to verify Gmail service connection")
        if not await agent_service.verify_connection():
            raise AIServiceException("Failed to verify agent service connection")
        if not vector_service.verify_connection():  # Synchronous call
            raise VectorDBException("Failed to verify vector service connection")
        
        logger.info("All services and agents initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise e  # Re-raise to prevent app startup with failed initialization
    
    yield
    
    # Shutdown
    try:
        vector_service.cleanup()  # Synchronous call
        logger.info("Services cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    
    logger.info("Shutting down Gmail Auto-Responder API...")

# Initialize FastAPI app
app = FastAPI(
    title="Gmail Auto-Responder API",
    description="AI-powered email auto-response system with Gmail integration",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add authentication middleware
# app.middleware("http")(auth_middleware)


# Include routers with proper prefixes
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(email_router, prefix="/api/emails", tags=["Emails"])
app.include_router(document_router, prefix="/api/documents", tags=["Documents"])
app.include_router(agent_router, prefix="/api/agents", tags=["Agents"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])

# Security
security = HTTPBearer()

# =============================================================================
# DEPENDENCY INJECTION
# =============================================================================

async def get_current_user(
    access_token: str = Cookie(None)
) -> dict:
    """Get current authenticated user from HTTP-only cookie"""
    try:
        if not access_token:
            raise AuthenticationException("Not authenticated")
        token_data = GmailAuthService.verify_token(access_token)
        if not token_data:
            raise AuthenticationException("Invalid token")
        return token_data
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise AuthenticationException("Invalid authentication credentials")

def get_auth_service() -> GmailAuthService:
    """Get Gmail authentication service"""
    return GmailAuthService()

def get_gmail_service(
    current_user: dict = Depends(get_current_user)
) -> GmailService:
    """Get Gmail service"""
    return GmailService(current_user)

def get_document_service(
    current_user: dict = Depends(get_current_user)
) -> DocumentService:
    """Get document service"""
    return DocumentService(current_user)

def get_vector_service() -> VectorService:
    """Get vector service"""
    return VectorService()

def get_agent_service(
    current_user: dict = Depends(get_current_user),
    vector_service: VectorService = Depends(get_vector_service)
) -> AgentService:
    """Get agent service"""
    # Create a new instance with the current user context and the pre-initialized agents
    base_agent_service = app.state.agent_service
    return AgentService(
        current_user=current_user,
        response_agent=base_agent_service.response_agent,
        context_agent=base_agent_service.context_agent,
        intent_agent=base_agent_service.intent_agent
    )



# =============================================================================
# SYSTEM ENDPOINTS
# =============================================================================

@app.get("/", response_model=SystemInfo)
async def root():
    """Root endpoint with system information"""
    return SystemInfo(
        name="Gmail Auto-Responder API",
        version="1.0.0",
        status="active",
        environment=settings.ENVIRONMENT
    )

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Comprehensive health check"""
    try:
        # Check Gmail service
        gmail_status = "healthy" if await GmailService.verify_connection() else "unhealthy"
        
        # Check Agent service
        agent_status = "healthy" if await AgentService.verify_connection() else "unhealthy"
        
        # Check Document service
        doc_status = "healthy" if await DocumentService.verify_connection() else "unhealthy"
        
        overall_status = "healthy" if all([
            gmail_status == "healthy",
            agent_status == "healthy",
            doc_status == "healthy"
        ]) else "unhealthy"
        
        return HealthCheck(
            status=overall_status,
            timestamp=datetime.utcnow(),
            services={
                "gmail_service": gmail_status,
                "agent_service": agent_status,
                "document_service": doc_status
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheck(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            services={
                "gmail_service": "unknown",
                "agent_service": "unknown",
                "document_service": "unknown"
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
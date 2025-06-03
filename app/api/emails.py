from fastapi import APIRouter, FastAPI, HTTPException, status, Depends
from typing import Optional
from app.models import schemas
from app.services.gmail_service import GmailService
from app.services.agent_service import AgentService
from app.services.vector_service import VectorService
from app.agents.response_generator import ResponseGeneratorAgent
from app.agents.context_retriever import ContextRetrieverAgent
from app.agents.intent_classifier import IntentClassifierAgent
from app.auth.gmail_auth import GmailAuthService
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# User-based key function
def user_rate_limit_key(request: Request):
    user = getattr(request.state, "user", None)
    if user and "email" in user:
        return user["email"]
    return get_remote_address(request)

user_limiter = Limiter(key_func=user_rate_limit_key)

def add_rate_limit_handler(app: FastAPI):
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logger = logging.getLogger(__name__)
router = APIRouter()

def get_gmail_service(current_user: dict = Depends(GmailAuthService.get_current_user)) -> GmailService:
    """Get Gmail service with auth"""
    try:
        # Extract credentials from current user
        credentials = current_user.get('tokens', {})
        user_email = current_user.get('email')
        
        if not credentials or not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        return GmailService(credentials, user_email)
    except Exception as e:
        logger.error(f"Failed to initialize Gmail service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize Gmail service: {str(e)}"
        )

def get_agent_service(current_user: dict = Depends(GmailAuthService.get_current_user)) -> AgentService:
    """Get agent service with auth"""
    try:
        # Initialize vector service first
        vector_service = VectorService()
        
        # Initialize agents with vector service
        response_agent = ResponseGeneratorAgent(vector_service=vector_service)
        context_agent = ContextRetrieverAgent(vector_service=vector_service)
        intent_agent = IntentClassifierAgent(vector_service=vector_service)
        
        # Create agent service with all components
        return AgentService(
            current_user=current_user,
            response_agent=response_agent,
            context_agent=context_agent,
            intent_agent=intent_agent
        )
    except Exception as e:
        logger.error(f"Failed to initialize agent service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize agent service: {str(e)}"
        )

@router.get("/", response_model=schemas.EmailListResponse)
async def list_emails(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    unread_only: bool = True,
    gmail_service: GmailService = Depends(get_gmail_service)
):
    """List emails with optional filtering"""
    try:
        # Build query string
        query_parts = []
        
        # Add unread filter
        if unread_only:
            query_parts.append("label:unread")
        
        # Add status filter if provided
        if status:
            query_parts.append(f"label:{status}")
            
        # Add search term if provided
        if search:
            query_parts.append(search)
            
        # Combine query parts
        query = " ".join(query_parts)
            
        emails = gmail_service.list_messages(
            max_results=limit,
            query=query.strip()
        )
        
        total = len(emails)
        
        # Transform the response to match the schema
        email_responses = [
            {
                "id": email["id"],
                "thread_id": email["thread_id"],
                "subject": email["subject"],
                "from": email["from"],
                "to": email["to"],
                "body": email["body"],
                "labels": email["labels"],
                "date": email["date"],
                "is_unread": "UNREAD" in email["labels"]
            }
            for email in emails
        ]
        
        return {
            "emails": email_responses,
            "total": total,
            "offset": offset,
            "limit": limit,
            "filters": {
                "unread_only": unread_only,
                "status": status,
                "search": search
            }
        }
    except Exception as e:
        logger.error(f"Failed to list emails: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list emails"
        )

@router.get("/{email_id}", response_model=schemas.EmailResponse)
async def get_email(
    email_id: str,
    gmail_service: GmailService = Depends(get_gmail_service)
):
    """Get specific email details"""
    try:
        email = gmail_service.get_message(email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        return email
    except Exception as e:
        logger.error(f"Failed to get email {email_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get email"
        )

@router.post("/{email_id}/reply")
@user_limiter.limit("3/minute")
async def reply_to_email(
    email_id: str,
    request: Request,
    reply: schemas.ReplyEmailRequest,
    gmail_service: GmailService = Depends(get_gmail_service),
    agent_service: AgentService = Depends(get_agent_service)
):
    """Reply to an email"""
    try:
        # Get original email
        email = gmail_service.get_message(email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        
        # If using generated response, get it first
        content = reply.content
        if reply.use_generated:
            generated = await agent_service.generate_response(
                email_content=email["body"],
                email_subject=email["subject"]
            )
            content = generated["content"]
        
        # Send reply
        response = gmail_service.send_message(
            to=email["from"],
            subject=f"Re: {email['subject']}",
            body=content,
            thread_id=email["thread_id"]
        )
        gmail_service.mark_as_read(email_id)  # Mark original email as read
        
        return {
            "message": "Reply sent successfully",
            "response_id": response["id"]
        }
    except Exception as e:
        logger.error(f"Failed to send reply: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reply"
        )
    
@router.post("/{email_id}/generate-response")
async def generate_email_response(
    email_id: str,
    agent_service: AgentService = Depends(get_agent_service),
    gmail_service: GmailService = Depends(get_gmail_service)
):
    """Generate a suggested reply for an email, but do not send it."""
    try:
        email = gmail_service.get_message(email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        generated = await agent_service.generate_response(
            email_content=email["body"],
            email_subject=email["subject"]
        )
        return {"content": generated["content"]}
    except Exception as e:
        logger.error(f"Failed to generate response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response"
        )

@router.get("/{email_id}/thread")
async def get_email_thread(
    email_id: str,
    gmail_service: GmailService = Depends(get_gmail_service)
):
    """Get all messages in an email thread"""
    try:
        # Get original email to get thread ID
        email = gmail_service.get_message(email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )
        
        # Get thread messages
        thread_messages = gmail_service.get_thread(email["thread_id"])
        return {"messages": thread_messages}
    except Exception as e:
        logger.error(f"Failed to get email thread: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get email thread"
        )

@router.get("/labels")
async def get_labels(
    gmail_service: GmailService = Depends(get_gmail_service)
):
    """Get Gmail labels/folders"""
    try:
        labels = gmail_service.get_labels()
        return {"labels": labels}
    except Exception as e:
        logger.error(f"Failed to get labels: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get labels"
        )

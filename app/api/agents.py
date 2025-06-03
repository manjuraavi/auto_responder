from fastapi import APIRouter, Depends, HTTPException, status
from app.models import schemas
from app.services.agent_service import AgentService
from app.auth.gmail_auth import GmailAuthService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_agent_service(auth_service: GmailAuthService = Depends(GmailAuthService)) -> AgentService:
    """Get agent service with auth"""
    return AgentService(auth_service)

@router.post("/generate-response", response_model=schemas.GeneratedResponse)
async def generate_ai_response(
    request: schemas.GenerateResponseRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Generate AI response for an email"""
    try:
        response = await agent_service.generate_response(
            email_id=request.email_id,
            context_length=request.context_length
        )
        return response
    except Exception as e:
        logger.error(f"Failed to generate response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response"
        )

@router.post("/classify-intent", response_model=schemas.IntentClassification)
async def classify_email_intent(
    request: schemas.ClassifyIntentRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Classify email intent"""
    try:
        classification = await agent_service.classify_intent(request.email_id)
        return classification
    except Exception as e:
        logger.error(f"Failed to classify intent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to classify intent"
        )

@router.post("/retrieve-context", response_model=schemas.ContextRetrieval)
async def retrieve_context(
    request: schemas.RetrieveContextRequest,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Retrieve relevant context for an email"""
    try:
        context = await agent_service.retrieve_context(
            email_id=request.email_id,
            query=request.query,
            max_results=request.max_results
        )
        return context
    except Exception as e:
        logger.error(f"Failed to retrieve context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve context"
        )

@router.put("/responses/{response_id}")
async def update_generated_response(
    response_id: int,
    content: str,
    agent_service: AgentService = Depends(get_agent_service)
):
    """Update a generated response"""
    try:
        updated_response = agent_service.update_response(response_id, content)
        return {
            "message": "Response updated successfully",
            "response_id": updated_response.id
        }
    except Exception as e:
        logger.error(f"Failed to update response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update response"
        )

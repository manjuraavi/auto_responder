from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Auth schemas
class AuthURL(BaseModel):
    auth_url: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_info: Dict[str, Any]

# Email schemas
class EmailBase(BaseModel):
    subject: str
    body: str
    from_email: EmailStr
    to_email: List[EmailStr]
    thread_id: Optional[str] = None
    labels: List[str] = []

class EmailResponse(BaseModel):
    id: str
    thread_id: str
    subject: str
    from_email: str = Field(..., alias='from')
    to_email: str = Field(..., alias='to')
    body: str
    labels: List[str]
    date: str

class EmailListResponse(BaseModel):
    emails: List[EmailResponse]
    total: int
    offset: int
    limit: int

class ReplyEmailRequest(BaseModel):
    content: Optional[str] = None
    use_generated: bool = True

# Document schemas
class EmailsToVectorRequest(BaseModel):
    """Request model for processing emails into vector store"""
    emails: List[Dict[str, Any]]

class DocumentBase(BaseModel):
    filename: str
    content_type: str

class DocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    status: str
    created_at: datetime

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    offset: int
    limit: int

class DocumentUploadResponse(BaseModel):
    document_ids: List[str]
    status: str
    message: str

# Agent schemas
class GenerateResponseRequest(BaseModel):
    email_content: str
    email_subject: str
    context_length: Optional[int] = 5

class GeneratedResponse(BaseModel):
    content: str
    context_used: List[Dict[str, Any]]
    confidence_score: float

class ClassifyIntentRequest(BaseModel):
    email_subject: str
    email_content: str

class IntentClassification(BaseModel):
    intent: str
    confidence: float
    entities: Dict[str, Any]

class RetrieveContextRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5

class ContextRetrieval(BaseModel):
    relevant_documents: List[Dict[str, Any]]
    similarity_scores: List[float]

# System schemas
class SystemInfo(BaseModel):
    """System information response model"""
    name: str = Field(description="Name of the system")
    version: str = Field(description="System version")
    status: str = Field(description="Current system status")
    environment: str = Field(description="Deployment environment")

class HealthCheck(BaseModel):
    """Health check response model"""
    status: str = Field(description="Overall system health status")
    timestamp: datetime = Field(description="Time of health check")
    services: Dict[str, str] = Field(description="Status of individual services")

class EmailIngestionRequest(BaseModel):
    days_back: int
    labels: Optional[List[str]] = None
    include_all_read: bool = False

class EmailIngestionResponse(BaseModel):
    processed_count: int
    status: str
    message: str


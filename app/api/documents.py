from fastapi import APIRouter, HTTPException, status, File, UploadFile, Depends
from typing import List, Dict, Any

from fastapi.responses import FileResponse
from app.models import schemas
from app.services.document_service import DocumentService
from app.auth.gmail_auth import GmailAuthService
from app.services.gmail_service import GmailService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_document_service(current_user: dict = Depends(GmailAuthService.get_current_user)) -> DocumentService:
    """Get document service with auth"""
    return DocumentService(current_user.get('sub'))

def get_gmail_service(current_user: dict = Depends(GmailAuthService.get_current_user)) -> GmailService:
    """Get Gmail service with auth"""
    try:
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

@router.post("/upload", response_model=schemas.DocumentUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    document_service: DocumentService = Depends(get_document_service)
):
    """Upload documents to vector store"""
    try:
        processed_docs = []
        for file in files:
            result = await document_service.process_document(file)
            processed_docs.append(result)
            
        return {
            "document_ids": [doc["id"] for doc in processed_docs],
            "status": "success",
            "message": f"Successfully processed {len(processed_docs)} documents"
        }
    except Exception as e:
        logger.error(f"Failed to upload documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload documents: {str(e)}"
        )

@router.post("/emails", response_model=schemas.DocumentUploadResponse)
async def process_emails(
    request: schemas.EmailsToVectorRequest,
    document_service: DocumentService = Depends(get_document_service)
):
    """Process emails into vector store"""
    try:
        processed_docs = []
        for email in request.emails:
            # Create a document from email
            doc_content = f"""
Subject: {email['subject']}
From: {email['from']}
To: {email['to']}
Body: {email['body']}
"""
            result = await document_service.process_email_content(
                content=doc_content,
                metadata={
                    "email_id": email['id'],
                    "thread_id": email['thread_id'],
                    "date": email['date']
                }
            )
            processed_docs.append(result)
            
        return {
            "document_ids": [doc["id"] for doc in processed_docs],
            "status": "success",
            "message": f"Successfully processed {len(processed_docs)} emails"
        }
    except Exception as e:
        logger.error(f"Failed to process emails: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process emails: {str(e)}"
        )
    
@router.get("/{doc_id}/download")
async def download_document(
    doc_id: str,
    document_service: DocumentService = Depends(get_document_service)
):
    """Download a document by ID"""
    try:
        file_path, filename = document_service.get_document_file(doc_id)
        return FileResponse(path=file_path, filename=filename, media_type="application/octet-stream")
    except Exception as e:
        logger.error(f"Failed to download document {doc_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
@router.get("/", response_model=schemas.DocumentListResponse)
async def list_documents(
    document_service: DocumentService = Depends(get_document_service)
):
    """List uploaded documents"""
    try:
        documents = await document_service.list_documents()
        return {
            "documents": documents,
            "total": len(documents),
            "offset": 0,
            "limit": len(documents)
        }
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )

@router.post("/query")
async def query_document(
    query: str,
    document_service: DocumentService = Depends(get_document_service)
):
    """Query similar content from documents"""
    try:
        results = document_service.query_similar(query)
        return {
            "results": results
        }
    except Exception as e:
        logger.error(f"Failed to query documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query documents"
        )

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    document_service: DocumentService = Depends(get_document_service)
):
    """Delete a document"""
    try:
        success = document_service.delete_document(doc_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {doc_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )

@router.post("/emails/ingest", response_model=schemas.EmailIngestionResponse)
async def ingest_emails(
    request: schemas.EmailIngestionRequest,
    gmail_service: GmailService = Depends(get_gmail_service),
    document_service: DocumentService = Depends(get_document_service)
):
    """Ingest emails into vector store based on filters"""
    try:
        # Calculate date filter
        date_after = (datetime.utcnow() - timedelta(days=request.days_back)).timestamp()
        
        # Build query string
        query_parts = []
        
        # Add date filter
        query_parts.append(f"after:{int(date_after)}")
        
        # Add label filters if specified
        if request.labels:
            label_queries = [f"label:{label}" for label in request.labels]
            query_parts.append(f"({' OR '.join(label_queries)})")
        
        # If not including all read emails, filter for read ones
        if not request.include_all_read:
            query_parts.append("-label:unread")
        
        # Get emails matching criteria
        query = " ".join(query_parts)
        emails = gmail_service.list_messages(
            max_results=500,  # Increased limit for bulk processing
            query=query
        )
        
        if not emails:
            return {
                "processed_count": 0,
                "status": "success",
                "message": "No emails found matching the criteria"
            }
        
        # Process emails in vector store
        processed_docs = []
        for email in emails:
            doc_content = f"""
Subject: {email['subject']}
From: {email['from']}
To: {email['to']}
Body: {email['body']}
"""
            result = await document_service.process_email_content(
                content=doc_content,
                metadata={
                    "email_id": email['id'],
                    "thread_id": email['thread_id'],
                    "date": email['date'],
                    "type": "email"
                }
            )
            processed_docs.append(result)
        
        return {
            "processed_count": len(processed_docs),
            "status": "success",
            "message": f"Successfully processed {len(processed_docs)} emails"
        }
        
    except Exception as e:
        logger.error(f"Failed to ingest emails: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest emails: {str(e)}"
        )

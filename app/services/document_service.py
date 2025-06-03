from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
import uuid
import os
from fastapi import UploadFile
import PyPDF2
import docx
import tiktoken
from io import BytesIO

from app.services.vector_service import VectorService
from app.utils.exceptions import DocumentServiceException
from app.config.settings import settings

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, user_id: str):
        """Initialize document service"""
        self.user_id = user_id
        self.vector_service = VectorService()
        self.vector_service.initialize()
        self.encoding = tiktoken.get_encoding("cl100k_base")

    @staticmethod
    async def verify_connection() -> bool:
        """Verify if document service and its dependencies are accessible"""
        try:
            # Create temporary service instance to test connection
            temp_service = DocumentService(user_id="health_check")
            
            # Check vector service connection
            if not temp_service.vector_service.verify_connection():
                logger.error("Vector service connection failed")
                return False
                
            # Check file system access for document processing
            test_dir = os.path.join(settings.UPLOAD_DIR, "health_check")
            os.makedirs(test_dir, exist_ok=True)
            test_file = os.path.join(test_dir, "test.txt")
            
            try:
                with open(test_file, "w") as f:
                    f.write("health check")
                os.remove(test_file)
                os.rmdir(test_dir)
            except Exception as e:
                logger.error(f"File system check failed: {str(e)}")
                return False
                
            logger.info("Document service health check passed")
            return True
            
        except Exception as e:
            logger.error(f"Document service health check failed: {str(e)}")
            return False

    async def process_document(self, file: UploadFile) -> Dict[str, Any]:
        """Process and store a document"""
        try:
            # Ensure vector service is initialized
            if not self.vector_service.verify_connection():
                self.vector_service.initialize()
            
            # Log file details for debugging
            logger.info(f"Processing file: {file.filename}, content_type: {file.content_type}")
            
            # Determine content type from filename if not provided
            content_type = file.content_type
            if not content_type:
                ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
                content_type_map = {
                    'pdf': 'application/pdf',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'doc': 'application/msword',
                    'txt': 'text/plain',
                    'md': 'text/markdown'
                }
                content_type = content_type_map.get(ext, 'text/plain')
                logger.info(f"Inferred content type from extension: {content_type}")
            
            # Validate file type
            if not self._is_valid_content_type(content_type):
                raise DocumentServiceException(f"Unsupported file type: {content_type} for file {file.filename}")
            
            # Read file content
            content = await self._read_file_content(file, content_type)
            
            # Store in vector DB
            doc_id = str(uuid.uuid4())
            self.vector_service.add_document(
                doc_id=doc_id,
                content=content,
                metadata={
                    "filename": file.filename,
                    "user_id": self.user_id,
                    "content_type": content_type,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            return {
                "id": doc_id,
                "filename": file.filename,
                "content_type": content_type,
                "status": "processed"
            }
            
        except Exception as e:
            logger.error(f"Failed to process document: {str(e)}")
            raise DocumentServiceException(f"Failed to process document: {str(e)}")

    def query_similar(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Query similar documents"""
        try:
            # Filter for user's documents
            filter_dict = {"user_id": self.user_id}
            
            return self.vector_service.query_similar(
                query=query,
                n_results=n_results,
                filter_dict=filter_dict
            )
        except Exception as e:
            logger.error(f"Failed to query similar documents: {str(e)}")
            raise DocumentServiceException(f"Failed to query similar documents: {str(e)}")

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document"""
        try:
            # Verify document belongs to user
            doc = self.vector_service.get_document(doc_id)
            if not doc or doc.get('metadata', {}).get('user_id') != self.user_id:
                return False
            
            self.vector_service.delete_document(doc_id)
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {str(e)}")
            raise DocumentServiceException(f"Failed to delete document: {str(e)}")

    async def _read_file_content(self, file: UploadFile, content_type: str) -> str:
        """Read and extract text content from file"""
        content = ""
        
        try:
            if content_type == "application/pdf":
                # Read PDF using BytesIO for proper file handling
                pdf_content = await file.read()
                pdf_file = BytesIO(pdf_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
                    
            elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                # Read DOCX using BytesIO
                doc_content = await file.read()
                doc_file = BytesIO(doc_content)
                doc = docx.Document(doc_file)
                
                for para in doc.paragraphs:
                    content += para.text + "\n"
                    
            else:
                # Read as plain text
                content = (await file.read()).decode('utf-8')
            
            # Truncate if too long (considering token limits)
            max_tokens = 8000  # Safe limit for embedding models
            tokens = self.encoding.encode(content)
            if len(tokens) > max_tokens:
                content = self.encoding.decode(tokens[:max_tokens])
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Failed to read file content: {str(e)}")
            raise DocumentServiceException(f"Failed to read file content: {str(e)}")
        finally:
            # Reset file pointer if possible
            try:
                await file.seek(0)
            except Exception:
                pass  # Ignore if seek isn't possible

    def _is_valid_content_type(self, content_type: str) -> bool:
        """Check if file type is supported"""
        valid_types = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "text/plain": "txt",
            # Add common MIME types for text files
            "text/markdown": "md",
            "text/x-markdown": "md",
            "application/x-pdf": "pdf",  # Alternative PDF MIME type
            "application/msword": "doc",  # Old Word format
        }
        
        if not content_type:
            return False
            
        # Log content type for debugging
        logger.info(f"Checking content type: {content_type}")
        return content_type.lower() in valid_types

    async def process_email_content(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process and store email content in vector DB"""
        try:
            gmail_id = metadata.get("gmail_id")
            if not gmail_id:
                raise DocumentServiceException("Missing gmail_id in email metadata")

            # Check for existing email by gmail_id to avoid duplicates
            existing_docs = self.vector_service.query_documents(
                filter_dict={"user_id": self.user_id, "gmail_id": gmail_id}
            )
            if existing_docs:
                logger.info(f"Email with gmail_id={gmail_id} already exists. Skipping insertion.")
                return {
                    "id": existing_docs[0]["id"],
                    "content_type": "email",
                    "status": "duplicate_skipped"
                }

            # Add user_id and other metadata
            metadata.update({
                "user_id": self.user_id,
                "content_type": "email",
                "created_at": datetime.utcnow().isoformat()
            })

            # Store in vector DB
            doc_id = str(uuid.uuid4())
            self.vector_service.add_document(
                doc_id=doc_id,
                content=content,
                metadata=metadata
            )

            return {
                "id": doc_id,
                "content_type": "email",
                "status": "processed"
            }

        except Exception as e:
            logger.error(f"Failed to process email content: {str(e)}")
            raise DocumentServiceException(f"Failed to process email content: {str(e)}")


    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents for the user"""
        try:
            # Query vector store for user's documents
            results = self.vector_service.query_documents(
                filter_dict={"user_id": self.user_id}
            )
            
            return [
                {
                    "id": doc["id"],
                    "filename": doc["metadata"].get("filename", "Email" if doc["metadata"].get("content_type") == "email" else "Unknown"),
                    "content_type": doc["metadata"].get("content_type", "unknown"),
                    "created_at": doc["metadata"].get("created_at", datetime.utcnow().isoformat()),
                    "status": "processed"
                }
                for doc in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            raise DocumentServiceException(f"Failed to list documents: {str(e)}")

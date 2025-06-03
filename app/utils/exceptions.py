# app/utils/exceptions.py
"""
Custom exceptions for the AI Email Assistant
"""

from typing import Optional, Any, Dict
from fastapi import HTTPException


class AIEmailAssistantException(Exception):
    """Base exception for AI Email Assistant."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AIEmailAssistantException):
    """Raised when authentication fails."""
    pass


class GmailAPIError(AIEmailAssistantException):
    """Raised when Gmail API operations fail."""
    pass


class VectorDatabaseError(AIEmailAssistantException):
    """Raised when vector database operations fail."""
    pass


class DocumentProcessingError(AIEmailAssistantException):
    """Raised when document processing fails."""
    pass


class AgentError(AIEmailAssistantException):
    """Raised when agent operations fail."""
    pass


class ConfigurationError(AIEmailAssistantException):
    """Raised when configuration is invalid."""
    pass


class ValidationError(AIEmailAssistantException):
    """Raised when data validation fails."""
    pass


class VectorDBException(AIEmailAssistantException):
    """Raised when vector database operations fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.status_code = 500  # Internal Server Error
        self.error_code = "VECTOR_DB_ERROR"

class DocumentServiceException(AIEmailAssistantException):
    """Raised when document service operations fail."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.status_code = 500  # Internal Server Error
        self.error_code = "DOCUMENT_SERVICE_ERROR"


class CustomHTTPException(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: str):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class AuthenticationException(CustomHTTPException):
    def __init__(self, detail: str, error_code: str = "AUTH_ERROR"):
        super().__init__(status_code=401, detail=detail, error_code=error_code)


class EmailServiceException(CustomHTTPException):
    def __init__(self, detail: str, error_code: str = "EMAIL_SERVICE_ERROR"):
        super().__init__(status_code=503, detail=detail, error_code=error_code)


class AIServiceException(CustomHTTPException):
    def __init__(self, detail: str, error_code: str = "AI_SERVICE_ERROR"):
        super().__init__(status_code=503, detail=detail, error_code=error_code)
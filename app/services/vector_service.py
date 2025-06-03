from typing import List, Optional, Any, Callable
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import os
from app.config.settings import settings
import logging
from app.utils.exceptions import VectorDBException
import time
from functools import wraps
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

def retry_operation(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry operations with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time:.1f}s: {str(e)}")
                        time.sleep(wait_time)
            raise last_exception
        return wrapper
    return decorator

class LocalSentenceTransformerEmbedding:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        return self.model.encode(input).tolist()

class VectorService:
    def __init__(self):
        """Initialize ChromaDB client with local embeddings"""
        self.client = None
        self.embedding_function = None
        self.collection = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize ChromaDB client"""
        if self._initialized:
            return

        try:
            # Initialize ChromaDB with persistence
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_PATH,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Use local sentence transformer embeddings
            self.embedding_function = LocalSentenceTransformerEmbedding()
            
            # Check if collection exists and its metadata
            try:
                existing_collection = self.client.get_collection(
                    name=settings.COLLECTION_NAME
                )
                collection_metadata = existing_collection.metadata or {}
                
                # If embedding model has changed, recreate collection
                if collection_metadata.get("embedding_model") != settings.EMBEDDING_MODEL:
                    logger.info(f"Embedding model changed. Recreating collection...")
                    self.client.delete_collection(settings.COLLECTION_NAME)
                    existing_collection = None
            except Exception:
                existing_collection = None
            
            # Create or get the collection
            self.collection = self.client.get_or_create_collection(
                name=settings.COLLECTION_NAME,
                embedding_function=self.embedding_function,
                metadata={"embedding_model": settings.EMBEDDING_MODEL}
            )
            
            self._initialized = True
            logger.info("VectorService initialized successfully with ChromaDB")
        except Exception as e:
            logger.error(f"Failed to initialize VectorService: {str(e)}")
            self._initialized = False
            raise VectorDBException(f"Failed to initialize vector database: {str(e)}")

    def verify_connection(self) -> bool:
        """Verify ChromaDB connection is working"""
        try:
            if not self._initialized or not self.client or not self.collection:
                return False
            # Try a simple operation to verify connection
            self.collection.count()
            return True
        except Exception as e:
            logger.error(f"Failed to verify ChromaDB connection: {str(e)}")
            self._initialized = False
            return False

    def ensure_initialized(self) -> None:
        """Ensure service is initialized before operations"""
        if not self._initialized or not self.verify_connection():
            self.initialize()

    def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.client:
                # ChromaDB doesn't require explicit cleanup
                self.client = None
                self.collection = None
                self.embedding_function = None
            logger.info("VectorService cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during VectorService cleanup: {str(e)}")

    @retry_operation()
    def add_document(self, doc_id: str, content: str, metadata: dict) -> None:
        """Add a document to the vector store"""
        self.ensure_initialized()
        try:
            self.collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            logger.info(f"Successfully added document {doc_id} to vector store")
        except Exception as e:
            logger.error(f"Failed to add document {doc_id} to vector store: {str(e)}")
            raise VectorDBException(f"Failed to add document to vector store: {str(e)}")

    @retry_operation()
    def query_similar(self, query: str, n_results: int = 5, filter_dict: Optional[dict] = None) -> List[dict]:
        """Query similar documents from the vector store"""
        self.ensure_initialized()
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_dict
            )
            
            # Format results
            documents = []
            for idx, doc in enumerate(results['documents'][0]):
                documents.append({
                    'content': doc,
                    'metadata': results['metadatas'][0][idx],
                    'distance': results['distances'][0][idx] if 'distances' in results else None,
                    'id': results['ids'][0][idx]
                })
            
            return documents
        except Exception as e:
            logger.error(f"Failed to query vector store: {str(e)}")
            raise VectorDBException(f"Failed to query vector store: {str(e)}")

    def delete_document(self, doc_id: str) -> None:
        """Delete a document from the vector store"""
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Successfully deleted document {doc_id} from vector store")
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id} from vector store: {str(e)}")
            raise VectorDBException(f"Failed to delete document from vector store: {str(e)}")

    def update_document(self, doc_id: str, content: str, metadata: dict) -> None:
        """Update a document in the vector store"""
        try:
            # ChromaDB doesn't have direct update, so we delete and add
            self.delete_document(doc_id)
            self.add_document(doc_id, content, metadata)
            logger.info(f"Successfully updated document {doc_id} in vector store")
        except Exception as e:
            logger.error(f"Failed to update document {doc_id} in vector store: {str(e)}")
            raise VectorDBException(f"Failed to update document in vector store: {str(e)}")

    def get_document(self, doc_id: str) -> Optional[dict]:
        """Get a document from the vector store by ID"""
        try:
            result = self.collection.get(ids=[doc_id])
            if result['documents']:
                return {
                    'content': result['documents'][0],
                    'metadata': result['metadatas'][0],
                    'id': doc_id
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get document {doc_id} from vector store: {str(e)}")
            raise VectorDBException(f"Failed to get document from vector store: {str(e)}")

    @retry_operation()
    def query_documents(self, filter_dict: Optional[dict] = None) -> List[dict]:
        """List all documents with optional filtering"""
        self.ensure_initialized()
        try:
            # Get all documents matching the filter
            results = self.collection.get(
                where=filter_dict
            )
            
            # Format results
            documents = []
            for idx, doc in enumerate(results['documents']):
                documents.append({
                    'content': doc,
                    'metadata': results['metadatas'][idx],
                    'id': results['ids'][idx]
                })
            
            return documents
        except Exception as e:
            logger.error(f"Failed to query documents: {str(e)}")
            raise VectorDBException(f"Failed to query documents: {str(e)}")

    def clear_collection(self) -> None:
        """Clear all documents from the collection"""
        try:
            self.collection.delete(ids=self.collection.get()['ids'])
            logger.info("Successfully cleared vector store collection")
        except Exception as e:
            logger.error(f"Failed to clear vector store collection: {str(e)}")
            raise VectorDBException(f"Failed to clear vector store: {str(e)}")
        
    def delete_emails(self, user_email: str):
        """
        Delete only emails from the vector DB for the given user.
        """
        try:
            self.collection.delete(where={"user_id": user_email, "type": "email"})
            logger.info(f"Deleted all emails for user {user_email}")
        except Exception as e:
            logger.error(f"Failed to delete emails for user {user_email}: {str(e)}")
            raise

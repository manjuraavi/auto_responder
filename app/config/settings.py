"""
Configuration management for AI Email Assistant
Handles environment variables and application settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings with validation and type checking."""

    # Application
    APP_NAME: str = "Gmail Auto-Responder"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Debug mode")

    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    RELOAD: bool = Field(default=True, description="Auto-reload on code changes")

    # Security
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT token expiration time")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")

    # CORS
    ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","))
    FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend URL for CORS")

    # OpenAI
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", description="OpenAI model to use")
    OPENAI_TEMPERATURE: float = Field(default=0.7, description="OpenAI temperature")
    OPENAI_MAX_TOKENS: int = Field(default=1000, description="OpenAI max tokens")

    # Google OAuth2
    GOOGLE_CLIENT_ID: str = Field(..., description="Google OAuth2 client ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., description="Google OAuth2 client secret")
    GOOGLE_REDIRECT_URI: str = Field(..., description="Google OAuth2 redirect URI")
    GMAIL_SCOPES: List[str] = Field(
        default=[
            "openid",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        description="Google OAuth2 scopes"
    )

    # Vector DB
    CHROMA_DB_PATH: str = Field(default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "vector_db"), description="Chroma database path")
    COLLECTION_NAME: str = Field(default="email_knowledge_base", description="Vector collection name")
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2", description="Embedding model")
    CHUNK_SIZE: int = Field(default=1000, description="Text chunk size for embeddings")
    CHUNK_OVERLAP: int = Field(default=200, description="Text chunk overlap")

    # File upload
    MAX_FILE_SIZE_MB: int = Field(default=10, description="Maximum file size in MB")
    ALLOWED_FILE_EXTENSIONS: List[str] = Field(
        default=[".txt", ".pdf", ".doc", ".docx", ".md"],
        description="Allowed file extensions"
    )
    UPLOAD_DIR: str = Field(default="./data/uploads", description="Upload directory")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    LOG_FILE: Optional[str] = Field(default="./logs/app.log", description="Log file path")

    # Agent
    MAX_CONTEXT_LENGTH: int = Field(default=4000, description="Maximum context length for agents")
    RETRIEVAL_TOP_K: int = Field(default=5, description="Top K results for retrieval")
    INTENT_CONFIDENCE_THRESHOLD: float = Field(default=0.7, description="Intent classification confidence threshold")

    # Email processing
    MAX_EMAILS_PER_BATCH: int = Field(default=50, description="Maximum emails to process per batch")
    EMAIL_SYNC_INTERVAL_MINUTES: int = Field(default=5, description="Email sync interval in minutes")

    # MongoDB
    MONGODB_URL: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    MONGODB_DB_NAME: str = Field(default="gmail_auto_responder", env="MONGODB_DB_NAME")

    # Additional
    MAX_RETRIES: int = Field(default=3, description="Maximum number of retries")
    RESPONSE_TIMEOUT: int = Field(default=30, description="Response timeout in seconds")

    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be 'development', 'staging', or 'production'")
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        if v not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")
        return v

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def IS_DEVELOPMENT(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def IS_PRODUCTION(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"

    def create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            self.CHROMA_DB_PATH,
            self.UPLOAD_DIR,
            os.path.dirname(self.LOG_FILE) if self.LOG_FILE else "./logs"
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                file_secret_settings,  # .env file takes precedence
                env_settings,  # environment variables are checked last
            )

# Add detailed debug prints for environment loading
print("\n=== Environment Configuration ===")
print(f"Looking for .env file in current directory")
print(f"Current working directory: {os.getcwd()}")
print(f"Absolute path to .env: {os.path.abspath('.env')}")
print(f"Does .env exist? {os.path.exists('.env')}")

try:
    with open('.env', 'r') as f:
        print("\nActual .env contents:")
        env_contents = f.read().splitlines()
        for line in env_contents:
            if line.strip() and not line.startswith('#'):
                key = line.split('=')[0].strip()
                value = line.split('=')[1].strip() if '=' in line else ''
                if 'SECRET' in key.upper() or 'KEY' in key.upper():
                    value = '********'
                print(f"{key}={value}")
except Exception as e:
    print(f"Error reading .env: {str(e)}")

print("\nEnvironment variables from os.environ:")
for key in ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI']:
    if key in os.environ:
        value = '********' if 'SECRET' in key else os.environ[key]
        print(f"{key}={value}")

# Global settings instance
settings = Settings()

# Print loaded values
print("\nLoaded Environment Variables:")
print(f"GOOGLE_CLIENT_ID: {'*' * 8}{settings.GOOGLE_CLIENT_ID[-8:] if settings.GOOGLE_CLIENT_ID else 'Not Set'}")
print(f"GOOGLE_REDIRECT_URI: {settings.GOOGLE_REDIRECT_URI if settings.GOOGLE_REDIRECT_URI else 'Not Set'}")
print(f"Environment: {settings.ENVIRONMENT}")
print("==============================\n")

# Create directories
settings.create_directories()

# Ensure ChromaDB directory exists
os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
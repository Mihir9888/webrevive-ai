"""Application configuration settings using pydantic-settings."""

from functools import lru_cache
from pathlib import Path
from typing import List, Set
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings class loaded from environment variables and .env file."""

    # Project Information
    PROJECT_NAME: str = "WebRevive AI"
    PROJECT_DESCRIPTION: str = "AI-Based Web Accessibility and Content Refactoring System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    DEBUG: bool = True

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./webrevive.db",
        description="Async database connection string (SQLite for dev, PostgreSQL for prod)",
    )

    # Local LLM (Ollama) Configuration
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Base URL for local Ollama service",
    )
    OLLAMA_MODEL: str = Field(
        default="qwen2.5-coder:7b",
        description="Default LLM model for accessibility analysis and refactoring",
    )
    OLLAMA_TIMEOUT_SECONDS: float = Field(
        default=90.0,
        description="Timeout in seconds for Ollama requests",
    )

    # File Upload Configuration
    UPLOAD_DIR: str = Field(
        default="./uploads",
        description="Directory for storing uploaded files and scan artifacts",
    )
    MAX_FILE_SIZE: int = Field(
        default=52428800,  # 50 MB
        description="Maximum allowed file size in bytes",
    )
    ALLOWED_EXTENSIONS: Set[str] = Field(
        default={".zip", ".html", ".htm", ".jsx", ".tsx", ".vue", ".js", ".ts"},
        description="Allowed file extensions for upload",
    )

    # Browser & Scanner Configuration
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT_MS: int = 45000
    AXE_CDN_URL: str = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js"

    # CORS Configuration
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def get_upload_path(self) -> Path:
        """Ensure upload directory exists and return Path object."""
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()

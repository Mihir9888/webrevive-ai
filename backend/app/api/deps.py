"""Dependency injection providers for FastAPI route handlers."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db as db_generator
from app.services.scanner import AccessibilityScanner, scanner
from app.services.ai_engine import AIEngine, ai_engine
from app.services.analyzer import CodeAnalyzer, code_analyzer
from app.services.refactorer import CodeRefactorer, code_refactorer
from app.services.validator import Validator, validator


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions."""
    async for session in db_generator():
        yield session


def get_scanner() -> AccessibilityScanner:
    """Dependency for obtaining the accessibility scanner service."""
    return scanner


def get_ai_engine() -> AIEngine:
    """Dependency for obtaining the Ollama AI remediation engine."""
    return ai_engine


def get_analyzer() -> CodeAnalyzer:
    """Dependency for obtaining the source code analyzer."""
    return code_analyzer


def get_refactorer() -> CodeRefactorer:
    """Dependency for obtaining the code refactoring service."""
    return code_refactorer


def get_validator() -> Validator:
    """Dependency for obtaining the verification validator."""
    return validator

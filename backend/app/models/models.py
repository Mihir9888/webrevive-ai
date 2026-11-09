"""SQLAlchemy ORM models for WebRevive AI."""

from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class Project(Base):
    """Project entity representing a scanned website or codebase repository."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    scans: Mapped[List["Scan"]] = relationship(
        "Scan", back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', url='{self.url}')>"


class Scan(Base):
    """Scan execution record containing summary metrics and status."""

    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, scanning, completed, failed
    scan_type: Mapped[str] = mapped_column(
        String(50), default="url", nullable=False
    )  # url, upload
    total_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    serious_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    moderate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minor_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="scans")
    issues: Mapped[List["AccessibilityIssue"]] = relationship(
        "AccessibilityIssue",
        back_populates="scan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    refactor_results: Mapped[List["RefactorResult"]] = relationship(
        "RefactorResult",
        back_populates="scan",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, status='{self.status}', total_issues={self.total_issues})>"


class AccessibilityIssue(Base):
    """Detailed accessibility violation record identified by axe-core or plugins."""

    __tablename__ = "accessibility_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    impact: Mapped[str] = mapped_column(
        String(50), nullable=False, default="moderate", index=True
    )  # critical, serious, moderate, minor
    description: Mapped[str] = mapped_column(Text, nullable=False)
    help_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    help_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    wcag_tags: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    html_source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    css_selector: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    target: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    fixed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="issues")
    suggestions: Mapped[List["AISuggestion"]] = relationship(
        "AISuggestion",
        back_populates="issue",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<AccessibilityIssue(id={self.id}, rule_id='{self.rule_id}', impact='{self.impact}')>"


class AISuggestion(Base):
    """AI-generated remediation proposal for an accessibility issue."""

    __tablename__ = "ai_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    issue_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accessibility_issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    original_code: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(50), default="html", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, approved, rejected, applied
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    issue: Mapped["AccessibilityIssue"] = relationship("AccessibilityIssue", back_populates="suggestions")
    refactor_results: Mapped[List["RefactorResult"]] = relationship(
        "RefactorResult", back_populates="suggestion", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<AISuggestion(id={self.id}, status='{self.status}', confidence={self.confidence_score})>"


class RefactorResult(Base):
    """Artifact of applied refactoring with unified diff and validation status."""

    __tablename__ = "refactor_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suggestion_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("ai_suggestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_file: Mapped[str] = mapped_column(String(1024), nullable=False)
    modified_file: Mapped[str] = mapped_column(String(1024), nullable=False)
    diff_content: Mapped[str] = mapped_column(Text, nullable=False)
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_result: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="refactor_results")
    suggestion: Mapped[Optional["AISuggestion"]] = relationship(
        "AISuggestion", back_populates="refactor_results"
    )

    def __repr__(self) -> str:
        return f"<RefactorResult(id={self.id}, applied={self.applied}, validated={self.validated})>"

"""Pydantic schemas for request validation and API serialization."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ScanTypeEnum(str, Enum):
    """Scan type categories."""
    URL = "url"
    UPLOAD = "upload"


class ScanStatusEnum(str, Enum):
    """Scan status lifecycle states."""
    PENDING = "pending"
    SCANNING = "scanning"
    COMPLETED = "completed"
    FAILED = "failed"


class ImpactLevelEnum(str, Enum):
    """Accessibility violation impact levels."""
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


class SuggestionStatusEnum(str, Enum):
    """Remediation suggestion status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


# ==================== Project Schemas ====================

class ProjectBase(BaseModel):
    name: str = Field(..., max_length=255, description="Project name")
    url: Optional[str] = Field(None, max_length=1024, description="Target website URL")
    description: Optional[str] = Field(None, description="Optional project description")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=1024)
    description: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    scans_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


# ==================== Suggestion Schemas ====================

class SuggestionBase(BaseModel):
    explanation: str
    original_code: str
    suggested_code: str
    language: str = "html"
    confidence_score: float = Field(default=0.85, ge=0.0, le=1.0)


class SuggestionCreate(SuggestionBase):
    issue_id: int


class SuggestionUpdate(BaseModel):
    status: SuggestionStatusEnum = Field(..., description="Target status (approved/rejected/applied)")


class SuggestionResponse(SuggestionBase):
    id: int
    issue_id: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Issue Schemas ====================

class IssueBase(BaseModel):
    rule_id: str
    impact: str
    description: str
    help_text: Optional[str] = None
    help_url: Optional[str] = None
    wcag_tags: List[str] = Field(default_factory=list)
    html_source: Optional[str] = None
    css_selector: Optional[str] = None
    target: List[Any] = Field(default_factory=list)
    fixed: bool = False


class IssueCreate(IssueBase):
    scan_id: int


class IssueUpdate(BaseModel):
    fixed: Optional[bool] = None


class IssueResponse(IssueBase):
    id: int
    scan_id: int
    created_at: datetime
    suggestions: List[SuggestionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ==================== Scan Schemas ====================

class ScanRequest(BaseModel):
    url: str = Field(..., description="Target URL to scan (e.g. https://example.com)")
    scan_type: ScanTypeEnum = Field(default=ScanTypeEnum.URL, description="Scan mode (url or upload)")
    project_id: Optional[int] = Field(default=None, description="Associated project ID")


class ScanResponse(BaseModel):
    id: int
    project_id: Optional[int]
    url: Optional[str]
    status: str
    scan_type: str
    total_issues: int
    critical_count: int
    serious_count: int
    moderate_count: int
    minor_count: int
    created_at: datetime
    completed_at: Optional[datetime]
    issues: List[IssueResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ScanSummaryResponse(BaseModel):
    id: int
    project_id: Optional[int]
    url: Optional[str]
    status: str
    scan_type: str
    total_issues: int
    critical_count: int
    serious_count: int
    moderate_count: int
    minor_count: int
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ==================== Refactor Schemas ====================

class RefactorRequest(BaseModel):
    suggestion_ids: List[int] = Field(..., min_length=1, description="List of approved suggestion IDs to apply")
    file_path: Optional[str] = Field(None, description="Optional specific target file path to patch")


class RefactorResultResponse(BaseModel):
    id: int
    scan_id: int
    suggestion_id: Optional[int]
    original_file: str
    modified_file: str
    diff_content: str
    applied: bool
    validated: bool
    validation_result: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RefactorResponse(BaseModel):
    scan_id: int
    applied_count: int
    failed_count: int
    results: List[RefactorResultResponse] = Field(default_factory=list)
    combined_diff: str = ""


class RollbackRequest(BaseModel):
    scan_id: int
    backup_file: Optional[str] = None


class RollbackResponse(BaseModel):
    success: bool
    message: str
    restored_files: List[str] = Field(default_factory=list)


# ==================== Report & Validation Schemas ====================

class SummaryStatsResponse(BaseModel):
    scan_id: int
    total_issues: int
    critical_count: int
    serious_count: int
    moderate_count: int
    minor_count: int
    wcag_compliance_score: float = Field(..., description="Estimated compliance score between 0 and 100")
    rules_violated_count: int
    top_violating_rules: List[Dict[str, Any]] = Field(default_factory=list)
    status: str


class ReportResponse(BaseModel):
    scan_id: int
    url: Optional[str]
    project: Optional[ProjectResponse] = None
    summary: SummaryStatsResponse
    issues: List[IssueResponse] = Field(default_factory=list)
    suggestions: List[SuggestionResponse] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationResponse(BaseModel):
    scan_id: int
    passed: bool
    issues_fixed: List[Dict[str, Any]] = Field(default_factory=list)
    issues_remaining: List[Dict[str, Any]] = Field(default_factory=list)
    new_issues: List[Dict[str, Any]] = Field(default_factory=list)
    fixed_count: int
    remaining_count: int
    new_count: int
    details: Optional[str] = None

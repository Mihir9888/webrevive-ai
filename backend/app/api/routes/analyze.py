"""AI analysis and remediation suggestion endpoints."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_ai_engine, get_db
from app.models.models import AccessibilityIssue, AISuggestion, Scan
from app.schemas.schemas import (
    SuggestionResponse,
    SuggestionStatusEnum,
    SuggestionUpdate,
)
from app.services.ai_engine import AIEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["AI Analysis"])


@router.post("/{scan_id}", response_model=List[SuggestionResponse], status_code=status.HTTP_200_OK)
async def analyze_scan_issues(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    ai_engine: AIEngine = Depends(get_ai_engine),
) -> List[SuggestionResponse]:
    """Execute AI remediation analysis on all unresolved accessibility issues for a scan."""
    # Verify scan existence
    scan_query = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan_obj = scan_query.scalar_one_or_none()
    if not scan_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found.",
        )

    # Query issues for this scan
    issues_query = await db.execute(
        select(AccessibilityIssue)
        .where(AccessibilityIssue.scan_id == scan_id)
        .options(selectinload(AccessibilityIssue.suggestions))
    )
    issues = issues_query.scalars().all()

    if not issues:
        return []

    created_suggestions: List[AISuggestion] = []

    for issue in issues:
        # Check if already has a pending or approved suggestion
        existing = [s for s in issue.suggestions if s.status in ["pending", "approved", "applied"]]
        if existing:
            created_suggestions.extend(existing)
            continue

        issue_dict = {
            "rule_id": issue.rule_id,
            "impact": issue.impact,
            "description": issue.description,
            "html_source": issue.html_source or "",
            "css_selector": issue.css_selector or "",
        }

        # Generate AI remediation fix
        try:
            fix_result = await ai_engine.generate_fix(
                issue=issue_dict,
                code_context=issue.html_source or "",
                language="html",
            )

            suggestion = AISuggestion(
                issue_id=issue.id,
                explanation=fix_result.get("explanation", "AI suggested fix."),
                original_code=fix_result.get("original_code", issue.html_source or ""),
                suggested_code=fix_result.get("suggested_code", issue.html_source or ""),
                language=fix_result.get("language", "html"),
                confidence_score=fix_result.get("confidence_score", 0.85),
                status=SuggestionStatusEnum.PENDING.value,
            )
            db.add(suggestion)
            created_suggestions.append(suggestion)

        except Exception as exc:
            logger.error(f"Error analyzing issue {issue.id}: {exc}")

    await db.commit()

    for s in created_suggestions:
        await db.refresh(s)

    return [SuggestionResponse.model_validate(s) for s in created_suggestions]


@router.get("/{scan_id}/suggestions", response_model=List[SuggestionResponse])
async def get_scan_suggestions(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> List[SuggestionResponse]:
    """Retrieve all generated remediation suggestions for a scan."""
    stmt = (
        select(AISuggestion)
        .join(AccessibilityIssue, AISuggestion.issue_id == AccessibilityIssue.id)
        .where(AccessibilityIssue.scan_id == scan_id)
        .order_by(AISuggestion.id.asc())
    )
    result = await db.execute(stmt)
    suggestions = result.scalars().all()
    return [SuggestionResponse.model_validate(s) for s in suggestions]


@router.get("/suggestion/{suggestion_id}", response_model=SuggestionResponse)
async def get_single_suggestion(
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
) -> SuggestionResponse:
    """Retrieve detail of a single AI suggestion by ID."""
    stmt = select(AISuggestion).where(AISuggestion.id == suggestion_id)
    result = await db.execute(stmt)
    suggestion = result.scalar_one_or_none()

    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suggestion with ID {suggestion_id} not found.",
        )

    return SuggestionResponse.model_validate(suggestion)


@router.put("/suggestion/{suggestion_id}", response_model=SuggestionResponse)
async def update_suggestion_status(
    suggestion_id: int,
    payload: SuggestionUpdate,
    db: AsyncSession = Depends(get_db),
) -> SuggestionResponse:
    """Update suggestion status (e.g., approve or reject recommendation)."""
    stmt = select(AISuggestion).where(AISuggestion.id == suggestion_id)
    result = await db.execute(stmt)
    suggestion = result.scalar_one_or_none()

    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suggestion with ID {suggestion_id} not found.",
        )

    suggestion.status = payload.status.value
    await db.commit()
    await db.refresh(suggestion)

    return SuggestionResponse.model_validate(suggestion)

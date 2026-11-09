"""Accessibility reporting and audit export endpoints."""

from collections import Counter
from datetime import datetime
import json
import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.models import AccessibilityIssue, Project, Scan
from app.schemas.schemas import (
    IssueResponse,
    ProjectResponse,
    ReportResponse,
    SuggestionResponse,
    SummaryStatsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


def _calculate_wcag_score(critical: int, serious: int, moderate: int, minor: int) -> float:
    """Calculate normalized WCAG 2.1 AA compliance score between 0.0 and 100.0."""
    penalty = (critical * 15.0) + (serious * 8.0) + (moderate * 3.0) + (minor * 1.0)
    score = max(0.0, min(100.0, 100.0 - penalty))
    return round(score, 1)


@router.get("/{scan_id}", response_model=ReportResponse)
async def get_full_report(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Generate comprehensive accessibility audit report for a specific scan."""
    stmt = (
        select(Scan)
        .where(Scan.id == scan_id)
        .options(
            selectinload(Scan.project),
            selectinload(Scan.issues).selectinload(AccessibilityIssue.suggestions),
        )
    )
    result = await db.execute(stmt)
    scan_obj = result.scalar_one_or_none()

    if not scan_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found.",
        )

    # Calculate rule statistics
    rule_counter = Counter(i.rule_id for i in scan_obj.issues)
    top_violating_rules = [
        {"rule_id": rule, "count": count}
        for rule, count in rule_counter.most_common(10)
    ]

    score = _calculate_wcag_score(
        scan_obj.critical_count,
        scan_obj.serious_count,
        scan_obj.moderate_count,
        scan_obj.minor_count,
    )

    summary = SummaryStatsResponse(
        scan_id=scan_obj.id,
        total_issues=scan_obj.total_issues,
        critical_count=scan_obj.critical_count,
        serious_count=scan_obj.serious_count,
        moderate_count=scan_obj.moderate_count,
        minor_count=scan_obj.minor_count,
        wcag_compliance_score=score,
        rules_violated_count=len(rule_counter),
        top_violating_rules=top_violating_rules,
        status=scan_obj.status,
    )

    all_suggestions: List[SuggestionResponse] = []
    for issue in scan_obj.issues:
        for s in issue.suggestions:
            all_suggestions.append(SuggestionResponse.model_validate(s))

    project_resp = (
        ProjectResponse.model_validate(scan_obj.project) if scan_obj.project else None
    )

    return ReportResponse(
        scan_id=scan_obj.id,
        url=scan_obj.url,
        project=project_resp,
        summary=summary,
        issues=[IssueResponse.model_validate(i) for i in scan_obj.issues],
        suggestions=all_suggestions,
        generated_at=datetime.utcnow(),
    )


@router.get("/{scan_id}/summary", response_model=SummaryStatsResponse)
async def get_report_summary(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> SummaryStatsResponse:
    """Retrieve summarized accessibility statistics and compliance scoring."""
    stmt = (
        select(Scan)
        .where(Scan.id == scan_id)
        .options(selectinload(Scan.issues))
    )
    result = await db.execute(stmt)
    scan_obj = result.scalar_one_or_none()

    if not scan_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found.",
        )

    rule_counter = Counter(i.rule_id for i in scan_obj.issues)
    top_violating_rules = [
        {"rule_id": rule, "count": count}
        for rule, count in rule_counter.most_common(10)
    ]

    score = _calculate_wcag_score(
        scan_obj.critical_count,
        scan_obj.serious_count,
        scan_obj.moderate_count,
        scan_obj.minor_count,
    )

    return SummaryStatsResponse(
        scan_id=scan_obj.id,
        total_issues=scan_obj.total_issues,
        critical_count=scan_obj.critical_count,
        serious_count=scan_obj.serious_count,
        moderate_count=scan_obj.moderate_count,
        minor_count=scan_obj.minor_count,
        wcag_compliance_score=score,
        rules_violated_count=len(rule_counter),
        top_violating_rules=top_violating_rules,
        status=scan_obj.status,
    )


@router.get("/{scan_id}/export")
async def export_report_json(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export the complete audit report as a downloadable JSON file."""
    report = await get_full_report(scan_id=scan_id, db=db)
    report_dict = report.model_dump(mode="json")
    json_bytes = json.dumps(report_dict, indent=2).encode("utf-8")

    filename = f"webrevive_audit_scan_{scan_id}.json"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "application/json",
    }
    return Response(content=json_bytes, media_type="application/json", headers=headers)

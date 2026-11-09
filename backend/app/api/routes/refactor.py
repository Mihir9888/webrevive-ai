"""Refactoring endpoints for applying code fixes, inspecting diffs, validating, and rolling back."""

import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_refactorer, get_validator
from app.models.models import (
    AccessibilityIssue,
    AISuggestion,
    RefactorResult,
    Scan,
)
from app.schemas.schemas import (
    RefactorRequest,
    RefactorResponse,
    RefactorResultResponse,
    RollbackRequest,
    RollbackResponse,
    SuggestionStatusEnum,
    ValidationResponse,
)
from app.services.refactorer import CodeRefactorer
from app.services.validator import Validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/refactor", tags=["Refactoring"])


@router.post("/{scan_id}", response_model=RefactorResponse, status_code=status.HTTP_200_OK)
async def apply_refactoring(
    scan_id: int,
    payload: RefactorRequest,
    db: AsyncSession = Depends(get_db),
    refactorer: CodeRefactorer = Depends(get_refactorer),
) -> RefactorResponse:
    """Apply selected approved accessibility suggestions and record unified diffs."""
    scan_query = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan_obj = scan_query.scalar_one_or_none()
    if not scan_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found.",
        )

    # Fetch targeted suggestions
    sugg_query = await db.execute(
        select(AISuggestion)
        .where(AISuggestion.id.in_(payload.suggestion_ids))
        .options(selectinload(AISuggestion.issue))
    )
    suggestions = sugg_query.scalars().all()

    if not suggestions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="None of the specified suggestion IDs were found.",
        )

    applied_results: List[RefactorResult] = []
    combined_diffs: List[str] = []
    failed_count = 0

    for sugg in suggestions:
        orig_code = sugg.original_code
        suggested_code = sugg.suggested_code
        file_target = payload.file_path or (scan_obj.url if scan_obj.scan_type == "upload" else "index.html")

        if payload.file_path and Path(payload.file_path).exists():
            # File system mutation
            res = refactorer.apply_fix_to_file(
                file_path=payload.file_path,
                original_snippet=orig_code,
                suggested_snippet=suggested_code,
                selector=sugg.issue.css_selector if sugg.issue else "",
            )
            diff_text = res.get("diff", "")
            is_applied = res.get("success", False)
        else:
            # In-memory virtual refactoring
            res = refactorer.apply_fix(
                original_code=orig_code,
                suggested_code=suggested_code,
                target_selector=sugg.issue.css_selector if sugg.issue else "",
                language=sugg.language,
            )
            diff_text = res.get("diff", "")
            is_applied = res.get("success", True)

        if is_applied:
            combined_diffs.append(diff_text)
            refactor_rec = RefactorResult(
                scan_id=scan_id,
                suggestion_id=sugg.id,
                original_file=file_target,
                modified_file=file_target,
                diff_content=diff_text or f"Applied fix for rule {sugg.issue.rule_id if sugg.issue else 'wcag'}",
                applied=True,
                validated=False,
            )
            db.add(refactor_rec)
            applied_results.append(refactor_rec)

            sugg.status = SuggestionStatusEnum.APPLIED.value
            if sugg.issue:
                sugg.issue.fixed = True
        else:
            failed_count += 1

    await db.commit()

    for r in applied_results:
        await db.refresh(r)

    return RefactorResponse(
        scan_id=scan_id,
        applied_count=len(applied_results),
        failed_count=failed_count,
        results=[RefactorResultResponse.model_validate(r) for r in applied_results],
        combined_diff="\n\n".join(combined_diffs),
    )


@router.get("/{scan_id}/diff", status_code=status.HTTP_200_OK)
async def get_refactoring_diff(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve full unified diff representation of all applied changes for a scan."""
    stmt = (
        select(RefactorResult)
        .where(RefactorResult.scan_id == scan_id)
        .order_by(RefactorResult.id.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    combined_diff = "\n\n".join(r.diff_content for r in records if r.diff_content)

    return {
        "scan_id": scan_id,
        "total_changes": len(records),
        "combined_diff": combined_diff,
        "results": [RefactorResultResponse.model_validate(r) for r in records],
    }


@router.post("/{scan_id}/validate", response_model=ValidationResponse, status_code=status.HTTP_200_OK)
async def validate_fixes(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    validator: Validator = Depends(get_validator),
) -> ValidationResponse:
    """Re-scan after refactoring to confirm resolution of issues and detect regressions."""
    scan_query = await db.execute(
        select(Scan)
        .where(Scan.id == scan_id)
        .options(selectinload(Scan.issues), selectinload(Scan.refactor_results))
    )
    scan_obj = scan_query.scalar_one_or_none()
    if not scan_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found.",
        )

    original_issues_list = [
        {
            "rule_id": i.rule_id,
            "css_selector": i.css_selector,
            "html_source": i.html_source,
            "target": i.target,
            "impact": i.impact,
        }
        for i in scan_obj.issues
    ]

    # Reconstruct modified source if files or patches exist
    modified_source = ""
    file_path: Optional[str] = None
    if scan_obj.refactor_results:
        # Check first modified file
        candidate_file = scan_obj.refactor_results[0].modified_file
        if Path(candidate_file).exists():
            file_path = candidate_file

    validation_data = await validator.validate_refactoring(
        scan_id=scan_id,
        original_issues=original_issues_list,
        modified_code=modified_source,
        file_path=file_path,
    )

    # Update refactor results with validation output
    for ref_res in scan_obj.refactor_results:
        ref_res.validated = True
        ref_res.validation_result = validation_data

    await db.commit()

    return ValidationResponse(
        scan_id=scan_id,
        passed=validation_data["passed"],
        issues_fixed=validation_data["issues_fixed"],
        issues_remaining=validation_data["issues_remaining"],
        new_issues=validation_data["new_issues"],
        fixed_count=validation_data["fixed_count"],
        remaining_count=validation_data["remaining_count"],
        new_count=validation_data["new_count"],
        details=validation_data["details"],
    )


@router.post("/{scan_id}/rollback", response_model=RollbackResponse, status_code=status.HTTP_200_OK)
async def rollback_refactoring(
    scan_id: int,
    payload: Optional[RollbackRequest] = None,
    db: AsyncSession = Depends(get_db),
    refactorer: CodeRefactorer = Depends(get_refactorer),
) -> RollbackResponse:
    """Roll back applied code modifications and revert suggestion states."""
    stmt = (
        select(RefactorResult)
        .where(RefactorResult.scan_id == scan_id)
        .options(selectinload(RefactorResult.suggestion).selectinload(AISuggestion.issue))
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    if not records:
        return RollbackResponse(
            success=True,
            message="No applied changes to rollback.",
            restored_files=[],
        )

    restored: List[str] = []
    for rec in records:
        rec.applied = False
        if rec.suggestion:
            rec.suggestion.status = SuggestionStatusEnum.APPROVED.value
            if rec.suggestion.issue:
                rec.suggestion.issue.fixed = False

        # Attempt disk rollback if backup file exists
        if rec.modified_file:
            mod_path = Path(rec.modified_file)
            backup_dir = mod_path.parent / ".webrevive_backups"
            if backup_dir.exists():
                backups = sorted(backup_dir.glob(f"{mod_path.name}.bak.*"), reverse=True)
                if backups:
                    if refactorer.rollback(str(backups[0]), str(mod_path)):
                        restored.append(str(mod_path))

    await db.commit()

    return RollbackResponse(
        success=True,
        message=f"Successfully rolled back {len(records)} refactoring changes.",
        restored_files=restored,
    )

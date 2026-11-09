"""Scan endpoints for URL scanning, file uploads, and issue queries."""

import asyncio
from datetime import datetime
import logging
import os
from pathlib import Path
import shutil
import zipfile
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_scanner
from app.core.config import settings
from app.models.database import async_session
from app.models.models import AccessibilityIssue, Project, Scan
from app.schemas.schemas import (
    IssueResponse,
    ScanRequest,
    ScanResponse,
    ScanSummaryResponse,
    ScanTypeEnum,
)
from app.services.scanner import AccessibilityScanner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["Scanning"])


async def _execute_scan_task(scan_id: int, target_url: str) -> None:
    """Background worker task executing URL scan and saving issues to database."""
    scanner = AccessibilityScanner()
    async with async_session() as session:
        try:
            # Mark scan as scanning
            scan_query = await session.execute(select(Scan).where(Scan.id == scan_id))
            scan_obj = scan_query.scalar_one_or_none()
            if not scan_obj:
                logger.error(f"Scan {scan_id} not found in database background task.")
                return

            scan_obj.status = "scanning"
            await session.commit()

            # Execute Playwright axe scan
            violations = await scanner.scan_url(target_url)

            # Categorize and aggregate issue counts
            critical = sum(1 for v in violations if v.get("impact") == "critical")
            serious = sum(1 for v in violations if v.get("impact") == "serious")
            moderate = sum(1 for v in violations if v.get("impact") == "moderate")
            minor = sum(1 for v in violations if v.get("impact") == "minor")

            # Persist individual issues
            for item in violations:
                issue = AccessibilityIssue(
                    scan_id=scan_id,
                    rule_id=item.get("rule_id", "wcag-rule"),
                    impact=item.get("impact", "moderate"),
                    description=item.get("description", ""),
                    help_text=item.get("help_text"),
                    help_url=item.get("help_url"),
                    wcag_tags=item.get("wcag_tags", []),
                    html_source=item.get("html_source"),
                    css_selector=item.get("css_selector"),
                    target=item.get("target", []),
                    fixed=False,
                )
                session.add(issue)

            # Update scan record
            scan_obj.status = "completed"
            scan_obj.total_issues = len(violations)
            scan_obj.critical_count = critical
            scan_obj.serious_count = serious
            scan_obj.moderate_count = moderate
            scan_obj.minor_count = minor
            scan_obj.completed_at = datetime.utcnow()

            await session.commit()
            logger.info(f"Scan {scan_id} finished successfully with {len(violations)} issues.")

        except Exception as exc:
            logger.error(f"Scan task error for scan {scan_id}: {exc}", exc_info=True)
            try:
                scan_query = await session.execute(select(Scan).where(Scan.id == scan_id))
                scan_obj = scan_query.scalar_one_or_none()
                if scan_obj:
                    scan_obj.status = "failed"
                    await session.commit()
            except Exception:
                pass


@router.post("/url", response_model=ScanSummaryResponse, status_code=status.HTTP_202_ACCEPTED)
async def scan_url_endpoint(
    payload: ScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ScanSummaryResponse:
    """Accept URL, create pending scan entry, and dispatch scan job to background."""
    # Verify project exists if project_id is supplied
    if payload.project_id:
        proj = await db.execute(select(Project).where(Project.id == payload.project_id))
        if not proj.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {payload.project_id} not found.",
            )

    new_scan = Scan(
        project_id=payload.project_id,
        url=str(payload.url),
        status="pending",
        scan_type="url",
        total_issues=0,
        critical_count=0,
        serious_count=0,
        moderate_count=0,
        minor_count=0,
    )
    db.add(new_scan)
    await db.commit()
    await db.refresh(new_scan)

    # Dispatch to background
    background_tasks.add_task(_execute_scan_task, new_scan.id, str(payload.url))

    return ScanSummaryResponse.model_validate(new_scan)


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan_details(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> ScanResponse:
    """Retrieve scan status, metrics, and associated issues."""
    stmt = (
        select(Scan)
        .where(Scan.id == scan_id)
        .options(selectinload(Scan.issues).selectinload(AccessibilityIssue.suggestions))
    )
    result = await db.execute(stmt)
    scan_obj = result.scalar_one_or_none()

    if not scan_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found.",
        )

    return ScanResponse.model_validate(scan_obj)


@router.get("/{scan_id}/issues", response_model=List[IssueResponse])
async def get_scan_issues(
    scan_id: int,
    impact: Optional[str] = Query(None, description="Filter by impact (critical/serious/moderate/minor)"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> List[IssueResponse]:
    """Retrieve paginated list of accessibility issues detected for a given scan."""
    query = (
        select(AccessibilityIssue)
        .where(AccessibilityIssue.scan_id == scan_id)
        .options(selectinload(AccessibilityIssue.suggestions))
        .offset(skip)
        .limit(limit)
        .order_by(desc(AccessibilityIssue.id))
    )

    if impact:
        query = query.where(AccessibilityIssue.impact == impact.lower())

    result = await db.execute(query)
    issues = result.scalars().all()
    return [IssueResponse.model_validate(i) for i in issues]


@router.post("/upload", response_model=ScanSummaryResponse, status_code=status.HTTP_201_CREATED)
async def upload_code_archive(
    file: UploadFile = File(...),
    project_id: Optional[int] = Query(None, description="Optional Project ID"),
    db: AsyncSession = Depends(get_db),
    scanner: AccessibilityScanner = Depends(get_scanner),
) -> ScanSummaryResponse:
    """Accept and scan a ZIP archive or standalone HTML/JSX/Vue file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file has no filename.")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension {ext} not supported. Allowed: {list(settings.ALLOWED_EXTENSIONS)}",
        )

    upload_root = settings.get_upload_path()
    scan_record = Scan(
        project_id=project_id,
        url=file.filename,
        status="scanning",
        scan_type="upload",
    )
    db.add(scan_record)
    await db.commit()
    await db.refresh(scan_record)

    scan_dir = upload_root / f"scan_{scan_record.id}"
    scan_dir.mkdir(parents=True, exist_ok=True)
    destination_file = scan_dir / file.filename

    # Save uploaded file
    with destination_file.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    all_violations: List[dict] = []

    try:
        if ext == ".zip":
            extract_dir = scan_dir / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(destination_file, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # Iterate over files and scan
            supported_exts = {".html", ".htm", ".jsx", ".tsx", ".vue"}
            for root, _, files in os.walk(extract_dir):
                for fname in files:
                    if Path(fname).suffix.lower() in supported_exts:
                        fpath = os.path.join(root, fname)
                        violations = await scanner.scan_file(fpath)
                        all_violations.extend(violations)
        else:
            # Standalone file scan
            all_violations = await scanner.scan_file(str(destination_file))

        # Persist issues
        critical = sum(1 for v in all_violations if v.get("impact") == "critical")
        serious = sum(1 for v in all_violations if v.get("impact") == "serious")
        moderate = sum(1 for v in all_violations if v.get("impact") == "moderate")
        minor = sum(1 for v in all_violations if v.get("impact") == "minor")

        for item in all_violations:
            issue = AccessibilityIssue(
                scan_id=scan_record.id,
                rule_id=item.get("rule_id", "wcag-rule"),
                impact=item.get("impact", "moderate"),
                description=item.get("description", ""),
                help_text=item.get("help_text"),
                help_url=item.get("help_url"),
                wcag_tags=item.get("wcag_tags", []),
                html_source=item.get("html_source"),
                css_selector=item.get("css_selector"),
                target=item.get("target", []),
            )
            db.add(issue)

        scan_record.status = "completed"
        scan_record.total_issues = len(all_violations)
        scan_record.critical_count = critical
        scan_record.serious_count = serious
        scan_record.moderate_count = moderate
        scan_record.minor_count = minor
        scan_record.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(scan_record)

    except Exception as exc:
        logger.error(f"Error scanning uploaded file: {exc}", exc_info=True)
        scan_record.status = "failed"
        await db.commit()
        await db.refresh(scan_record)

    return ScanSummaryResponse.model_validate(scan_record)


@router.delete("/{scan_id}", status_code=status.HTTP_200_OK)
async def delete_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a scan and all associated issues and suggestions."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan_obj = result.scalar_one_or_none()
    if not scan_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found.",
        )

    await db.execute(delete(Scan).where(Scan.id == scan_id))
    await db.commit()

    return {"message": f"Scan {scan_id} and associated records successfully deleted."}

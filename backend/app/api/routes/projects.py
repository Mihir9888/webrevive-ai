"""Project management CRUD endpoints."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.models.models import Project, Scan
from app.schemas.schemas import ProjectCreate, ProjectResponse, ProjectUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    """List all registered projects ordered by most recent creation date."""
    stmt = (
        select(Project)
        .options(selectinload(Project.scans))
        .offset(skip)
        .limit(limit)
        .order_by(Project.created_at.desc())
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()

    response_list = []
    for p in projects:
        data = ProjectResponse.model_validate(p)
        data.scans_count = len(p.scans)
        response_list.append(data)

    return response_list


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new project tracking target accessibility refactoring."""
    project = Project(
        name=payload.name,
        url=payload.url,
        description=payload.description,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    resp = ProjectResponse.model_validate(project)
    resp.scans_count = 0
    return resp


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Retrieve detailed project information and scan history."""
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.scans))
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found.",
        )

    resp = ProjectResponse.model_validate(project)
    resp.scans_count = len(project.scans)
    return resp


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Update metadata for an existing project."""
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.scans))
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found.",
        )

    if payload.name is not None:
        project.name = payload.name
    if payload.url is not None:
        project.url = payload.url
    if payload.description is not None:
        project.description = payload.description

    await db.commit()
    await db.refresh(project)

    resp = ProjectResponse.model_validate(project)
    resp.scans_count = len(project.scans)
    return resp


@router.delete("/{project_id}", status_code=status.HTTP_200_OK)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete a project and all associated scans, issues, and artifacts."""
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found.",
        )

    await db.delete(project)
    await db.commit()

    return {"message": f"Project {project_id} and all related records deleted."}

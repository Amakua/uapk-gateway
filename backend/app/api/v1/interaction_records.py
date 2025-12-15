"""Interaction record API endpoints - audit log access."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, RequireOrgViewer
from app.models.interaction_record import Decision
from app.schemas.interaction_record import (
    InteractionRecordList,
    InteractionRecordQuery,
    InteractionRecordResponse,
)
from app.services.interaction_record import InteractionRecordService

router = APIRouter(prefix="/orgs/{org_id}/records", tags=["Interaction Records"])


@router.get("", response_model=InteractionRecordList)
async def list_interaction_records(
    org_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgViewer],
    agent_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    decision: Decision | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> InteractionRecordList:
    """List interaction records (audit log) for an organization.

    Supports filtering by agent, action, decision, and time range.
    Records are returned in reverse chronological order.
    """
    record_service = InteractionRecordService(db)

    query = InteractionRecordQuery(
        agent_id=agent_id,
        action=action,
        decision=decision,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    return await record_service.list_records(org_id=org_id, query=query)


@router.get("/{record_id}", response_model=InteractionRecordResponse)
async def get_interaction_record(
    org_id: UUID,
    record_id: str,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgViewer],
) -> InteractionRecordResponse:
    """Get a specific interaction record by ID."""
    record_service = InteractionRecordService(db)
    record = await record_service.get_record_by_id(record_id)

    if record is None or record.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found",
        )

    return InteractionRecordResponse.model_validate(record)


@router.get("/verify/integrity")
async def verify_chain_integrity(
    org_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgViewer],
    limit: int = Query(default=1000, ge=1, le=10000),
) -> dict:
    """Verify the integrity of the interaction record chain.

    Checks that the chain of records has not been tampered with.
    Returns verification results including any broken links.
    """
    record_service = InteractionRecordService(db)
    return await record_service.verify_chain_integrity(org_id=org_id, limit=limit)

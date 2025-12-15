"""Policy API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, RequireOrgAdmin
from app.schemas.policy import (
    PolicyCreate,
    PolicyList,
    PolicyResponse,
    PolicyUpdate,
)
from app.services.policy import PolicyService

router = APIRouter(prefix="/orgs/{org_id}/policies", tags=["Policies"])


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    org_id: UUID,
    data: PolicyCreate,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> PolicyResponse:
    """Create a new policy.

    Policies define rules for evaluating agent action requests:
    - ALLOW: Explicitly allow matching actions
    - DENY: Block matching actions
    - REQUIRE_APPROVAL: Require human approval for matching actions
    """
    if data.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="org_id in path must match org_id in body",
        )

    policy_service = PolicyService(db)
    policy = await policy_service.create_policy(data, user_id=user.id)
    return PolicyResponse.model_validate(policy)


@router.get("", response_model=PolicyList)
async def list_policies(
    org_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
    enabled_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> PolicyList:
    """List policies for an organization."""
    policy_service = PolicyService(db)
    return await policy_service.list_policies(
        org_id=org_id,
        enabled_only=enabled_only,
        limit=limit,
        offset=offset,
    )


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    org_id: UUID,
    policy_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> PolicyResponse:
    """Get a specific policy."""
    policy_service = PolicyService(db)
    policy = await policy_service.get_policy_by_id(policy_id)

    if policy is None or policy.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    return PolicyResponse.model_validate(policy)


@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    org_id: UUID,
    policy_id: UUID,
    data: PolicyUpdate,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> PolicyResponse:
    """Update a policy."""
    policy_service = PolicyService(db)

    existing = await policy_service.get_policy_by_id(policy_id)
    if existing is None or existing.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    policy = await policy_service.update_policy(policy_id, data)
    return PolicyResponse.model_validate(policy)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    org_id: UUID,
    policy_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> None:
    """Delete a policy."""
    policy_service = PolicyService(db)

    existing = await policy_service.get_policy_by_id(policy_id)
    if existing is None or existing.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )

    await policy_service.delete_policy(policy_id)

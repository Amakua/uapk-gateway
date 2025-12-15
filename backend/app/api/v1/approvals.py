"""API endpoints for approval workflow."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.approval import ApprovalStatus
from app.models.user import User
from app.schemas.approval import (
    ApprovalDecisionResponse,
    ApprovalList,
    ApprovalResponse,
    ApprovalStats,
    ApproveRequest,
    DenyRequest,
)
from app.services import approval as approval_service
from app.services.approval import ApprovalError

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=ApprovalList)
async def list_approvals(
    status_filter: ApprovalStatus | None = Query(None, alias="status"),
    uapk_id: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApprovalList:
    """List approvals for the organization.

    Args:
        status: Filter by approval status
        uapk_id: Filter by UAPK ID
        limit: Maximum number of results (1-100)
        offset: Offset for pagination
    """
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    return await approval_service.list_approvals(
        db=db,
        org_id=current_user.default_org_id,
        status_filter=status_filter,
        uapk_id=uapk_id,
        limit=limit,
        offset=offset,
    )


@router.get("/pending", response_model=list[ApprovalResponse])
async def get_pending_approvals(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ApprovalResponse]:
    """Get pending approvals for the organization.

    Also automatically marks expired approvals.
    """
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    return await approval_service.get_pending_approvals(
        db=db,
        org_id=current_user.default_org_id,
        limit=limit,
    )


@router.get("/stats", response_model=ApprovalStats)
async def get_approval_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApprovalStats:
    """Get approval statistics for the organization."""
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    return await approval_service.get_approval_stats(
        db=db,
        org_id=current_user.default_org_id,
    )


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApprovalResponse:
    """Get a specific approval by ID."""
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    approval = await approval_service.get_approval(
        db=db,
        org_id=current_user.default_org_id,
        approval_id=approval_id,
    )

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval '{approval_id}' not found",
        )

    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalDecisionResponse)
async def approve_action(
    approval_id: str,
    request: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApprovalDecisionResponse:
    """Approve an escalated action.

    Returns an override token that can be used to execute
    the action without policy checks.

    The override token:
    - Is bound to the specific action (by hash)
    - Has a short expiry (default 5 minutes)
    - Can only be used once
    """
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        return await approval_service.approve_action(
            db=db,
            org_id=current_user.default_org_id,
            approval_id=approval_id,
            request=request,
            user_id=str(current_user.id),
        )
    except ApprovalError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{approval_id}/deny", response_model=ApprovalDecisionResponse)
async def deny_action(
    approval_id: str,
    request: DenyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApprovalDecisionResponse:
    """Deny an escalated action.

    The action will not be executed, and the agent will
    receive a denial response.
    """
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        return await approval_service.deny_action(
            db=db,
            org_id=current_user.default_org_id,
            approval_id=approval_id,
            request=request,
            user_id=str(current_user.id),
        )
    except ApprovalError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

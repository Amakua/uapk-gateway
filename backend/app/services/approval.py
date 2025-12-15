"""Service layer for approval workflow."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capability_jwt import create_override_token
from app.core.logging import get_logger
from app.models.approval import Approval, ApprovalStatus
from app.schemas.approval import (
    ApprovalDecisionResponse,
    ApprovalList,
    ApprovalResponse,
    ApprovalStats,
    ApproveRequest,
    DenyRequest,
)

logger = get_logger("services.approval")


class ApprovalError(Exception):
    """Raised when approval operations fail."""

    pass


async def get_approval(
    db: AsyncSession,
    org_id: UUID,
    approval_id: str,
) -> ApprovalResponse | None:
    """Get an approval by ID.

    Args:
        db: Database session
        org_id: Organization ID
        approval_id: Approval identifier

    Returns:
        Approval response or None if not found
    """
    result = await db.execute(
        select(Approval).where(
            Approval.org_id == org_id,
            Approval.approval_id == approval_id,
        )
    )
    approval = result.scalar_one_or_none()

    if approval:
        return ApprovalResponse.model_validate(approval)
    return None


async def list_approvals(
    db: AsyncSession,
    org_id: UUID,
    status_filter: ApprovalStatus | None = None,
    uapk_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ApprovalList:
    """List approvals for an organization.

    Args:
        db: Database session
        org_id: Organization ID
        status_filter: Optional status to filter by
        uapk_id: Optional UAPK ID to filter by
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of approval responses with counts
    """
    # Build base query
    query = select(Approval).where(Approval.org_id == org_id)

    if status_filter:
        query = query.where(Approval.status == status_filter)

    if uapk_id:
        query = query.where(Approval.uapk_id == uapk_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get pending count
    pending_query = select(func.count()).where(
        Approval.org_id == org_id,
        Approval.status == ApprovalStatus.PENDING,
    )
    pending_result = await db.execute(pending_query)
    pending_count = pending_result.scalar() or 0

    # Get results with pagination
    query = query.order_by(Approval.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    approvals = result.scalars().all()

    return ApprovalList(
        items=[ApprovalResponse.model_validate(a) for a in approvals],
        total=total,
        pending_count=pending_count,
    )


async def get_pending_approvals(
    db: AsyncSession,
    org_id: UUID,
    limit: int = 50,
) -> list[ApprovalResponse]:
    """Get pending approvals for an organization.

    Also marks expired approvals as expired.
    """
    now = datetime.now(UTC)

    # First, mark expired approvals
    expired_query = select(Approval).where(
        Approval.org_id == org_id,
        Approval.status == ApprovalStatus.PENDING,
        Approval.expires_at < now,
    )
    expired_result = await db.execute(expired_query)
    expired_approvals = expired_result.scalars().all()

    for approval in expired_approvals:
        approval.status = ApprovalStatus.EXPIRED
        approval.decided_at = now

    if expired_approvals:
        await db.commit()
        logger.info(
            "approvals_expired",
            org_id=str(org_id),
            count=len(expired_approvals),
        )

    # Now get pending approvals
    query = (
        select(Approval)
        .where(
            Approval.org_id == org_id,
            Approval.status == ApprovalStatus.PENDING,
        )
        .order_by(Approval.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    approvals = result.scalars().all()

    return [ApprovalResponse.model_validate(a) for a in approvals]


async def approve_action(
    db: AsyncSession,
    org_id: UUID,
    approval_id: str,
    request: ApproveRequest,
    user_id: str,
) -> ApprovalDecisionResponse:
    """Approve an action and generate override token.

    Args:
        db: Database session
        org_id: Organization ID
        approval_id: Approval identifier
        request: Approval request with notes
        user_id: ID of user approving

    Returns:
        Decision response with override token

    Raises:
        ApprovalError: If approval fails
    """
    result = await db.execute(
        select(Approval).where(
            Approval.org_id == org_id,
            Approval.approval_id == approval_id,
        )
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise ApprovalError(f"Approval '{approval_id}' not found")

    if approval.status != ApprovalStatus.PENDING:
        raise ApprovalError(
            f"Approval '{approval_id}' is not pending (status: {approval.status.value})"
        )

    # Check if expired
    now = datetime.now(UTC)
    if approval.expires_at and approval.expires_at < now:
        approval.status = ApprovalStatus.EXPIRED
        approval.decided_at = now
        await db.commit()
        raise ApprovalError(f"Approval '{approval_id}' has expired")

    # Calculate action hash for override token
    action_hash = _compute_action_hash(approval.action)

    # Generate override token
    override_token = create_override_token(
        org_id=str(org_id),
        uapk_id=approval.uapk_id,
        agent_id=approval.agent_id,
        action_hash=action_hash,
        approval_id=approval_id,
        expires_in_seconds=request.override_token_expires_in_seconds,
    )

    # Update approval status
    approval.status = ApprovalStatus.APPROVED
    approval.decided_at = now
    approval.decided_by = user_id
    approval.decision_notes = request.notes

    await db.commit()

    logger.info(
        "approval_approved",
        org_id=str(org_id),
        approval_id=approval_id,
        decided_by=user_id,
        action_hash=action_hash,
    )

    override_expires_at = datetime.fromtimestamp(
        now.timestamp() + request.override_token_expires_in_seconds, tz=UTC
    )

    return ApprovalDecisionResponse(
        approval_id=approval_id,
        status=ApprovalStatus.APPROVED,
        decided_at=now,
        decided_by=user_id,
        override_token=override_token,
        override_token_expires_at=override_expires_at,
    )


async def deny_action(
    db: AsyncSession,
    org_id: UUID,
    approval_id: str,
    request: DenyRequest,
    user_id: str,
) -> ApprovalDecisionResponse:
    """Deny an action.

    Args:
        db: Database session
        org_id: Organization ID
        approval_id: Approval identifier
        request: Denial request with reason/notes
        user_id: ID of user denying

    Returns:
        Decision response

    Raises:
        ApprovalError: If denial fails
    """
    result = await db.execute(
        select(Approval).where(
            Approval.org_id == org_id,
            Approval.approval_id == approval_id,
        )
    )
    approval = result.scalar_one_or_none()

    if not approval:
        raise ApprovalError(f"Approval '{approval_id}' not found")

    if approval.status != ApprovalStatus.PENDING:
        raise ApprovalError(
            f"Approval '{approval_id}' is not pending (status: {approval.status.value})"
        )

    now = datetime.now(UTC)

    # Build notes
    notes = request.notes
    if request.reason:
        notes = f"Reason: {request.reason}" + (f"\n{notes}" if notes else "")

    # Update approval status
    approval.status = ApprovalStatus.DENIED
    approval.decided_at = now
    approval.decided_by = user_id
    approval.decision_notes = notes

    await db.commit()

    logger.info(
        "approval_denied",
        org_id=str(org_id),
        approval_id=approval_id,
        decided_by=user_id,
        reason=request.reason,
    )

    return ApprovalDecisionResponse(
        approval_id=approval_id,
        status=ApprovalStatus.DENIED,
        decided_at=now,
        decided_by=user_id,
        override_token=None,
        override_token_expires_at=None,
    )


async def get_approval_stats(
    db: AsyncSession,
    org_id: UUID,
) -> ApprovalStats:
    """Get approval statistics for an organization."""
    # Get counts by status
    query = select(
        Approval.status,
        func.count().label("count"),
    ).where(
        Approval.org_id == org_id
    ).group_by(Approval.status)

    result = await db.execute(query)
    rows = result.all()

    stats = {
        ApprovalStatus.PENDING: 0,
        ApprovalStatus.APPROVED: 0,
        ApprovalStatus.DENIED: 0,
        ApprovalStatus.EXPIRED: 0,
    }

    for row in rows:
        stats[row.status] = row.count

    total = sum(stats.values())

    return ApprovalStats(
        pending=stats[ApprovalStatus.PENDING],
        approved=stats[ApprovalStatus.APPROVED],
        denied=stats[ApprovalStatus.DENIED],
        expired=stats[ApprovalStatus.EXPIRED],
        total=total,
    )


def _compute_action_hash(action: dict) -> str:
    """Compute a hash of the action for override token binding."""
    # Sort keys for deterministic hashing
    action_json = json.dumps(action, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(action_json.encode()).hexdigest()[:16]

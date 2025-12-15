"""Tests for approval workflow."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval, ApprovalStatus
from app.schemas.approval import ApproveRequest, DenyRequest
from app.services import approval as approval_service
from app.services.approval import ApprovalError


@pytest_asyncio.fixture
async def test_approval(db_session: AsyncSession, test_org) -> Approval:
    """Create a test approval."""
    approval = Approval(
        id=uuid4(),
        approval_id=f"appr-test-{uuid4().hex[:8]}",
        org_id=test_org.id,
        interaction_id=f"int-test-{uuid4().hex[:8]}",
        uapk_id="test-uapk",
        agent_id="test-agent",
        action={
            "type": "payment",
            "tool": "stripe_transfer",
            "params": {"amount": 1000, "currency": "USD"},
        },
        counterparty={"id": "vendor-123", "type": "merchant"},
        context={"conversation_id": "conv-123"},
        reason_codes=["amount_requires_approval"],
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    db_session.add(approval)
    await db_session.flush()
    return approval


@pytest_asyncio.fixture
async def expired_approval(db_session: AsyncSession, test_org) -> Approval:
    """Create an expired approval."""
    approval = Approval(
        id=uuid4(),
        approval_id=f"appr-expired-{uuid4().hex[:8]}",
        org_id=test_org.id,
        interaction_id=f"int-expired-{uuid4().hex[:8]}",
        uapk_id="test-uapk",
        agent_id="test-agent",
        action={"type": "payment", "tool": "stripe_transfer", "params": {}},
        reason_codes=["budget_threshold_reached"],
        status=ApprovalStatus.PENDING,
        expires_at=datetime.now(UTC) - timedelta(hours=1),  # Already expired
    )
    db_session.add(approval)
    await db_session.flush()
    return approval


class TestApprovalService:
    """Test approval service functions."""

    @pytest.mark.asyncio
    async def test_get_approval(self, db_session: AsyncSession, test_approval: Approval):
        """Test getting an approval by ID."""
        result = await approval_service.get_approval(
            db=db_session,
            org_id=test_approval.org_id,
            approval_id=test_approval.approval_id,
        )

        assert result is not None
        assert result.approval_id == test_approval.approval_id
        assert result.status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_approval_not_found(self, db_session: AsyncSession, test_org):
        """Test getting a non-existent approval."""
        result = await approval_service.get_approval(
            db=db_session,
            org_id=test_org.id,
            approval_id="appr-nonexistent",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_approval_wrong_org(
        self, db_session: AsyncSession, test_approval: Approval
    ):
        """Test getting an approval from wrong org."""
        result = await approval_service.get_approval(
            db=db_session,
            org_id=uuid4(),  # Different org
            approval_id=test_approval.approval_id,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_list_approvals(self, db_session: AsyncSession, test_approval: Approval):
        """Test listing approvals."""
        result = await approval_service.list_approvals(
            db=db_session,
            org_id=test_approval.org_id,
        )

        assert result.total >= 1
        assert any(a.approval_id == test_approval.approval_id for a in result.items)

    @pytest.mark.asyncio
    async def test_list_approvals_filter_by_status(
        self, db_session: AsyncSession, test_approval: Approval
    ):
        """Test filtering approvals by status."""
        # Filter for pending
        result = await approval_service.list_approvals(
            db=db_session,
            org_id=test_approval.org_id,
            status_filter=ApprovalStatus.PENDING,
        )

        assert all(a.status == ApprovalStatus.PENDING for a in result.items)

    @pytest.mark.asyncio
    async def test_approve_action(
        self, db_session: AsyncSession, test_approval: Approval
    ):
        """Test approving an action."""
        result = await approval_service.approve_action(
            db=db_session,
            org_id=test_approval.org_id,
            approval_id=test_approval.approval_id,
            request=ApproveRequest(notes="Approved for testing"),
            user_id="user-123",
        )

        assert result.status == ApprovalStatus.APPROVED
        assert result.decided_by == "user-123"
        assert result.override_token is not None
        assert result.override_token_expires_at is not None

    @pytest.mark.asyncio
    async def test_approve_generates_valid_override_token(
        self, db_session: AsyncSession, test_approval: Approval
    ):
        """Test that approval generates a valid override token."""
        from app.core.capability_jwt import verify_capability_token

        result = await approval_service.approve_action(
            db=db_session,
            org_id=test_approval.org_id,
            approval_id=test_approval.approval_id,
            request=ApproveRequest(),
            user_id="user-123",
        )

        # Verify the token is valid
        claims, error = verify_capability_token(result.override_token)

        assert error is None
        assert claims is not None
        assert claims.approval_id == test_approval.approval_id
        assert claims.action_hash is not None

    @pytest.mark.asyncio
    async def test_deny_action(
        self, db_session: AsyncSession, test_approval: Approval
    ):
        """Test denying an action."""
        result = await approval_service.deny_action(
            db=db_session,
            org_id=test_approval.org_id,
            approval_id=test_approval.approval_id,
            request=DenyRequest(reason="Suspicious activity", notes="Test denial"),
            user_id="user-123",
        )

        assert result.status == ApprovalStatus.DENIED
        assert result.decided_by == "user-123"
        assert result.override_token is None

    @pytest.mark.asyncio
    async def test_cannot_approve_already_approved(
        self, db_session: AsyncSession, test_approval: Approval
    ):
        """Test that approved actions cannot be approved again."""
        # First approve
        await approval_service.approve_action(
            db=db_session,
            org_id=test_approval.org_id,
            approval_id=test_approval.approval_id,
            request=ApproveRequest(),
            user_id="user-123",
        )

        # Try to approve again
        with pytest.raises(ApprovalError) as exc_info:
            await approval_service.approve_action(
                db=db_session,
                org_id=test_approval.org_id,
                approval_id=test_approval.approval_id,
                request=ApproveRequest(),
                user_id="user-456",
            )

        assert "not pending" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_cannot_deny_already_denied(
        self, db_session: AsyncSession, test_approval: Approval
    ):
        """Test that denied actions cannot be denied again."""
        # First deny
        await approval_service.deny_action(
            db=db_session,
            org_id=test_approval.org_id,
            approval_id=test_approval.approval_id,
            request=DenyRequest(),
            user_id="user-123",
        )

        # Try to deny again
        with pytest.raises(ApprovalError) as exc_info:
            await approval_service.deny_action(
                db=db_session,
                org_id=test_approval.org_id,
                approval_id=test_approval.approval_id,
                request=DenyRequest(),
                user_id="user-456",
            )

        assert "not pending" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_approve_expired_approval(
        self, db_session: AsyncSession, expired_approval: Approval
    ):
        """Test that expired approvals cannot be approved."""
        with pytest.raises(ApprovalError) as exc_info:
            await approval_service.approve_action(
                db=db_session,
                org_id=expired_approval.org_id,
                approval_id=expired_approval.approval_id,
                request=ApproveRequest(),
                user_id="user-123",
            )

        assert "expired" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_approval_stats(
        self, db_session: AsyncSession, test_approval: Approval
    ):
        """Test getting approval statistics."""
        stats = await approval_service.get_approval_stats(
            db=db_session,
            org_id=test_approval.org_id,
        )

        assert stats.pending >= 1
        assert stats.total >= 1

    @pytest.mark.asyncio
    async def test_get_pending_approvals_expires_old(
        self, db_session: AsyncSession, expired_approval: Approval
    ):
        """Test that get_pending_approvals marks expired ones."""
        # Get pending - this should mark expired approval
        await approval_service.get_pending_approvals(
            db=db_session,
            org_id=expired_approval.org_id,
        )

        # Refresh and check status
        await db_session.refresh(expired_approval)
        assert expired_approval.status == ApprovalStatus.EXPIRED

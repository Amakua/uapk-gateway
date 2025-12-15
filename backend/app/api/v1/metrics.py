"""Metrics endpoint for observability."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Response
from sqlalchemy import func, select

from app.api.deps import DbSession
from app.models.action_counter import ActionCounter
from app.models.approval import Approval, ApprovalStatus
from app.models.interaction_record import Decision, InteractionRecord

router = APIRouter(tags=["Metrics"])


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics(db: DbSession) -> Response:
    """Prometheus metrics endpoint.

    Exposes:
    - uapk_gateway_requests_total (by decision)
    - uapk_gateway_approvals_pending
    - uapk_gateway_daily_actions_total
    """
    metrics = []

    # Get today's request counts by decision
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=UTC)

    for decision in Decision:
        result = await db.execute(
            select(func.count(InteractionRecord.id)).where(
                InteractionRecord.timestamp >= today_start,
                InteractionRecord.decision == decision,
            )
        )
        count = result.scalar() or 0
        metrics.append(
            f'uapk_gateway_requests_total{{decision="{decision.value}"}} {count}'
        )

    # Get pending approvals count
    result = await db.execute(
        select(func.count(Approval.id)).where(
            Approval.status == ApprovalStatus.PENDING,
        )
    )
    pending_approvals = result.scalar() or 0
    metrics.append(f"uapk_gateway_approvals_pending {pending_approvals}")

    # Get total actions today (all orgs)
    result = await db.execute(
        select(func.sum(ActionCounter.count)).where(
            ActionCounter.counter_date == date.today(),
        )
    )
    total_actions = result.scalar() or 0
    metrics.append(f"uapk_gateway_daily_actions_total {total_actions}")

    # Build response
    content = "\n".join(metrics) + "\n"
    return Response(content=content, media_type="text/plain; charset=utf-8")

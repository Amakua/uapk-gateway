"""Action gateway service - the core of UAPK.

This service handles agent action requests, evaluating policies,
enforcing capabilities, and logging tamper-evident interaction records.
"""

import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_capability_token_jwt
from app.models.interaction_record import Decision
from app.models.policy import PolicyType
from app.schemas.action import (
    ActionRequest,
    ActionResponse,
    PolicyEvaluationResult,
)
from app.services.capability_token import CapabilityTokenService
from app.services.interaction_record import InteractionRecordService
from app.services.policy import PolicyEvaluator, PolicyService


class ActionGatewayService:
    """Core gateway service for processing agent action requests."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.token_service = CapabilityTokenService(db)
        self.record_service = InteractionRecordService(db)
        self.policy_service = PolicyService(db)
        self.policy_evaluator = PolicyEvaluator(self.policy_service)

    async def process_action(
        self,
        jwt_token: str,
        request: ActionRequest,
    ) -> ActionResponse:
        """Process an agent action request.

        This is the main gateway endpoint flow:
        1. Validate the capability token
        2. Check the action is in granted capabilities
        3. Evaluate policies
        4. Create interaction record
        5. Return decision
        """
        start_time = time.monotonic()

        # Decode and validate the JWT
        payload = decode_capability_token_jwt(jwt_token)
        if payload is None:
            return await self._create_denied_response(
                org_id=None,
                agent_id="unknown",
                request=request,
                reason="Invalid or expired capability token",
                start_time=start_time,
            )

        token_id = payload.get("sub")
        agent_id = payload.get("agent_id")
        org_id_str = payload.get("org_id")
        capabilities = payload.get("capabilities", [])

        if not all([token_id, agent_id, org_id_str]):
            return await self._create_denied_response(
                org_id=None,
                agent_id=agent_id or "unknown",
                request=request,
                reason="Malformed capability token",
                start_time=start_time,
            )

        org_id = UUID(org_id_str)

        # Validate the token in the database
        token, error = await self.token_service.validate_token(token_id)
        if error:
            return await self._create_denied_response(
                org_id=org_id,
                agent_id=agent_id,
                request=request,
                reason=error,
                start_time=start_time,
            )

        # Evaluate policies
        decision_type, evaluations, reason = await self.policy_evaluator.evaluate(
            org_id=org_id,
            action=request.action,
            agent_id=agent_id,
            capabilities=capabilities,
            parameters=request.parameters,
        )

        # Map policy type to decision
        if decision_type == PolicyType.ALLOW:
            decision = Decision.APPROVED
        elif decision_type == PolicyType.DENY:
            decision = Decision.DENIED
        else:  # REQUIRE_APPROVAL
            decision = Decision.PENDING

        # Calculate duration
        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Create interaction record
        record = await self.record_service.create_record(
            org_id=org_id,
            agent_id=agent_id,
            action=request.action,
            request={
                "parameters": request.parameters,
                "context": request.context.model_dump() if request.context else None,
                "idempotency_key": request.idempotency_key,
            },
            decision=decision,
            decision_reason=reason,
            policy_evaluations=evaluations,
            result=None,  # Would be populated by action execution
            duration_ms=duration_ms,
            capability_token_id=token.id if token else None,
        )

        # Increment token action count
        if token and decision == Decision.APPROVED:
            await self.token_service.increment_action_count(token)

        return ActionResponse(
            record_id=record.record_id,
            decision=decision,
            decision_reason=reason,
            policy_evaluations=[
                PolicyEvaluationResult(
                    policy_id=e["policy_id"],
                    policy_name=e.get("policy_name", ""),
                    result=e["result"],
                    reason=e.get("reason"),
                )
                for e in evaluations
            ] if evaluations else None,
            result=None,
            timestamp=record.timestamp,
            duration_ms=duration_ms,
        )

    async def _create_denied_response(
        self,
        org_id: UUID | None,
        agent_id: str,
        request: ActionRequest,
        reason: str,
        start_time: float,
    ) -> ActionResponse:
        """Create a denied response and log it."""
        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Create record if we have org_id
        if org_id:
            record = await self.record_service.create_record(
                org_id=org_id,
                agent_id=agent_id,
                action=request.action,
                request={
                    "parameters": request.parameters,
                    "context": request.context.model_dump() if request.context else None,
                    "idempotency_key": request.idempotency_key,
                },
                decision=Decision.DENIED,
                decision_reason=reason,
                duration_ms=duration_ms,
            )
            record_id = record.record_id
            timestamp = record.timestamp
        else:
            record_id = "error-no-org"
            timestamp = datetime.now(UTC)

        return ActionResponse(
            record_id=record_id,
            decision=Decision.DENIED,
            decision_reason=reason,
            policy_evaluations=None,
            result=None,
            timestamp=timestamp,
            duration_ms=duration_ms,
        )

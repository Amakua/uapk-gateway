"""Gateway service - orchestrates evaluate and execute flows."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import (
    canonicalize_json,
    compute_record_hash,
    compute_request_hash,
    compute_result_hash,
    sign_record_hash,
)
from app.core.config import get_settings
from app.core.encryption import EncryptionError, decrypt_value
from app.core.logging import get_logger
from app.gateway.connectors import (
    ConnectorConfig,
    ConnectorResult,
    HttpRequestConnector,
    MockConnector,
    ToolConnector,
    WebhookConnector,
)
from app.gateway.policy_engine import PolicyContext, PolicyEngine, PolicyResult
from app.models.approval import Approval, ApprovalStatus
from app.models.interaction_record import Decision, InteractionRecord
from app.models.secret import Secret
from app.schemas.gateway import (
    ActionInfo,
    CounterpartyInfo,
    GatewayActionRequest,
    GatewayDecision,
    GatewayDecisionResponse,
    GatewayExecuteResponse,
    ReasonCode,
    ReasonDetail,
    ToolResult,
)

logger = get_logger("gateway.service")


def generate_interaction_id() -> str:
    """Generate a unique interaction ID."""
    return f"int-{secrets.token_hex(12)}"


def generate_approval_id() -> str:
    """Generate a unique approval ID."""
    return f"appr-{secrets.token_hex(12)}"


class GatewayService:
    """Gateway service for evaluating and executing agent actions."""

    # Registry of connector types
    CONNECTOR_TYPES: dict[str, type[ToolConnector]] = {
        "webhook": WebhookConnector,
        "http": HttpRequestConnector,
        "http_request": HttpRequestConnector,
        "mock": MockConnector,
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.policy_engine = PolicyEngine(db)

    async def evaluate(
        self,
        org_id: UUID,
        request: GatewayActionRequest,
    ) -> GatewayDecisionResponse:
        """Evaluate an action request without executing.

        Returns the policy decision and reasons.
        """
        interaction_id = generate_interaction_id()

        logger.info(
            "gateway_evaluate_start",
            interaction_id=interaction_id,
            org_id=str(org_id),
            uapk_id=request.uapk_id,
            agent_id=request.agent_id,
            action_type=request.action.type,
            tool=request.action.tool,
        )

        # Build policy context
        context = PolicyContext(
            org_id=org_id,
            uapk_id=request.uapk_id,
            agent_id=request.agent_id,
            action=request.action,
            counterparty=request.counterparty,
            capability_token=request.capability_token,
        )

        # Evaluate policies
        policy_result = await self.policy_engine.evaluate(context)

        # Create approval if escalated
        approval_id = None
        if policy_result.decision == GatewayDecision.ESCALATE:
            approval_id = await self._create_approval(
                org_id=org_id,
                interaction_id=interaction_id,
                request=request,
                policy_result=policy_result,
            )

        # Log the interaction record
        await self._create_interaction_record(
            org_id=org_id,
            interaction_id=interaction_id,
            request=request,
            policy_result=policy_result,
            executed=False,
            tool_result=None,
        )

        timestamp = datetime.now(UTC)

        logger.info(
            "gateway_evaluate_complete",
            interaction_id=interaction_id,
            decision=policy_result.decision.value,
            reason_codes=[r.code.value for r in policy_result.reasons],
            approval_id=approval_id,
        )

        return GatewayDecisionResponse(
            interaction_id=interaction_id,
            decision=policy_result.decision,
            reasons=policy_result.reasons,
            approval_id=approval_id,
            timestamp=timestamp,
            policy_version="0.1",
        )

    async def execute(
        self,
        org_id: UUID,
        request: GatewayActionRequest,
    ) -> GatewayExecuteResponse:
        """Evaluate and execute an action request.

        If ALLOW: executes the tool connector and returns result.
        If DENY: returns decision without execution.
        If ESCALATE: creates approval task and returns decision.
        """
        interaction_id = generate_interaction_id()

        logger.info(
            "gateway_execute_start",
            interaction_id=interaction_id,
            org_id=str(org_id),
            uapk_id=request.uapk_id,
            agent_id=request.agent_id,
            action_type=request.action.type,
            tool=request.action.tool,
        )

        # Build policy context
        context = PolicyContext(
            org_id=org_id,
            uapk_id=request.uapk_id,
            agent_id=request.agent_id,
            action=request.action,
            counterparty=request.counterparty,
            capability_token=request.capability_token,
        )

        # Evaluate policies
        policy_result = await self.policy_engine.evaluate(context)

        executed = False
        tool_result: ToolResult | None = None
        approval_id: str | None = None

        if policy_result.decision == GatewayDecision.ALLOW:
            # Execute the tool
            executed = True
            connector_result = await self._execute_tool(
                org_id=org_id,
                manifest=policy_result.manifest,
                request=request,
            )

            tool_result = ToolResult(
                success=connector_result.success,
                data=connector_result.data,
                error=connector_result.error,
                result_hash=connector_result.result_hash,
                duration_ms=connector_result.duration_ms,
            )

            # Increment budget counter
            await self.policy_engine.increment_budget(org_id, request.uapk_id)

        elif policy_result.decision == GatewayDecision.ESCALATE:
            approval_id = await self._create_approval(
                org_id=org_id,
                interaction_id=interaction_id,
                request=request,
                policy_result=policy_result,
            )

        # Log the interaction record
        await self._create_interaction_record(
            org_id=org_id,
            interaction_id=interaction_id,
            request=request,
            policy_result=policy_result,
            executed=executed,
            tool_result=tool_result,
        )

        timestamp = datetime.now(UTC)

        logger.info(
            "gateway_execute_complete",
            interaction_id=interaction_id,
            decision=policy_result.decision.value,
            executed=executed,
            tool_success=tool_result.success if tool_result else None,
            approval_id=approval_id,
        )

        return GatewayExecuteResponse(
            interaction_id=interaction_id,
            decision=policy_result.decision,
            reasons=policy_result.reasons,
            approval_id=approval_id,
            timestamp=timestamp,
            policy_version="0.1",
            executed=executed,
            result=tool_result,
        )

    async def _execute_tool(
        self,
        org_id: UUID,
        manifest: Any,
        request: GatewayActionRequest,
    ) -> ConnectorResult:
        """Execute the tool using the appropriate connector."""
        if manifest is None:
            return ConnectorResult(
                success=False,
                error={"code": "NO_MANIFEST", "message": "No manifest available"},
            )

        manifest_json = manifest.manifest_json
        tool_registry = manifest_json.get("tools", {})
        tool_config = tool_registry.get(request.action.tool)

        if tool_config is None:
            # If no specific tool config, check if there's a default connector
            default_connector = manifest_json.get("default_connector")
            if default_connector:
                tool_config = default_connector
            else:
                return ConnectorResult(
                    success=False,
                    error={
                        "code": "TOOL_NOT_CONFIGURED",
                        "message": f"Tool '{request.action.tool}' not configured in manifest",
                    },
                )

        # Build connector config
        connector_type = tool_config.get("connector_type", "mock")

        if connector_type not in self.CONNECTOR_TYPES:
            return ConnectorResult(
                success=False,
                error={
                    "code": "INVALID_CONNECTOR_TYPE",
                    "message": f"Unknown connector type: {connector_type}",
                },
            )

        config = ConnectorConfig(
            connector_type=connector_type,
            url=tool_config.get("url"),
            method=tool_config.get("method", "POST"),
            headers=tool_config.get("headers", {}),
            timeout_seconds=tool_config.get(
                "timeout_seconds",
                self.settings.gateway_connector_timeout_seconds,
            ),
            secret_refs=tool_config.get("secret_refs", {}),
            extra=tool_config.get("extra", {}),
        )

        # Resolve secrets
        secrets = await self._resolve_secrets(org_id, config.secret_refs)

        # Create connector instance
        connector_class = self.CONNECTOR_TYPES[connector_type]
        connector = connector_class(config, secrets)

        # Execute
        return await connector.execute(request.action.params)

    async def _resolve_secrets(
        self,
        org_id: UUID,
        secret_refs: dict[str, str],
    ) -> dict[str, str]:
        """Resolve secret references to decrypted values."""
        if not secret_refs:
            return {}

        secrets_result: dict[str, str] = {}
        secret_names = list(set(secret_refs.values()))

        for secret_name in secret_names:
            result = await self.db.execute(
                select(Secret).where(
                    Secret.org_id == org_id,
                    Secret.name == secret_name,
                )
            )
            secret = result.scalar_one_or_none()

            if secret is not None:
                try:
                    decrypted = decrypt_value(secret.encrypted_value)
                    secrets_result[secret_name] = decrypted
                except EncryptionError:
                    logger.warning(
                        "secret_decryption_failed",
                        org_id=str(org_id),
                        secret_name=secret_name,
                    )

        return secrets_result

    async def _create_approval(
        self,
        org_id: UUID,
        interaction_id: str,
        request: GatewayActionRequest,
        policy_result: PolicyResult,
    ) -> str:
        """Create an approval task for escalated actions."""
        approval_id = generate_approval_id()

        expires_at = datetime.now(UTC) + timedelta(
            hours=self.settings.gateway_approval_expiry_hours
        )

        approval = Approval(
            approval_id=approval_id,
            org_id=org_id,
            interaction_id=interaction_id,
            uapk_id=request.uapk_id,
            agent_id=request.agent_id,
            action=request.action.model_dump(),
            counterparty=request.counterparty.model_dump() if request.counterparty else None,
            context=request.context,
            reason_codes=[r.code.value for r in policy_result.reasons],
            status=ApprovalStatus.PENDING,
            expires_at=expires_at,
        )

        self.db.add(approval)
        await self.db.flush()

        logger.info(
            "approval_created",
            approval_id=approval_id,
            interaction_id=interaction_id,
            org_id=str(org_id),
            uapk_id=request.uapk_id,
            expires_at=expires_at.isoformat(),
        )

        return approval_id

    async def _create_interaction_record(
        self,
        org_id: UUID,
        interaction_id: str,
        request: GatewayActionRequest,
        policy_result: PolicyResult,
        executed: bool,
        tool_result: ToolResult | None,
    ) -> InteractionRecord:
        """Create a tamper-evident interaction record for audit logging.

        The record is:
        - Hash-chained to the previous record for this UAPK
        - Signed by the gateway's Ed25519 key
        - Contains a full policy trace
        """
        # Map gateway decision to DB decision
        decision_map = {
            GatewayDecision.ALLOW: Decision.APPROVED,
            GatewayDecision.DENY: Decision.DENIED,
            GatewayDecision.ESCALATE: Decision.PENDING,
        }
        decision = decision_map[policy_result.decision]

        # Build request data for hashing
        request_data = {
            "uapk_id": request.uapk_id,
            "agent_id": request.agent_id,
            "action": request.action.model_dump(),
            "counterparty": request.counterparty.model_dump() if request.counterparty else None,
            "context": request.context,
            "capability_token_provided": request.capability_token is not None,
        }
        request_hash = compute_request_hash(request_data)

        # Build result dict and hash
        result_dict = None
        result_hash_value = None
        if tool_result:
            result_dict = tool_result.model_dump()
            result_hash_value = compute_result_hash(result_dict)

        # Build reasons JSON
        reasons_data = [r.model_dump() for r in policy_result.reasons]
        reasons_json = canonicalize_json(reasons_data)

        # Build policy trace JSON
        policy_trace_data = {
            "checks": policy_result.policy_trace,
        }
        policy_trace_json = canonicalize_json(policy_trace_data)

        # Build risk snapshot JSON
        risk_snapshot_json = None
        if policy_result.risk_indicators:
            risk_snapshot_json = canonicalize_json(policy_result.risk_indicators)

        # Get the previous record hash for this UAPK (hash chain)
        previous_record = await self.db.execute(
            select(InteractionRecord)
            .where(
                InteractionRecord.org_id == org_id,
                InteractionRecord.uapk_id == request.uapk_id,
            )
            .order_by(desc(InteractionRecord.created_at))
            .limit(1)
        )
        prev_record = previous_record.scalar_one_or_none()
        previous_record_hash = prev_record.record_hash if prev_record else None

        # Get current timestamp
        created_at = datetime.now(UTC)

        # Compute record hash
        record_hash = compute_record_hash(
            record_id=interaction_id,
            org_id=str(org_id),
            uapk_id=request.uapk_id,
            agent_id=request.agent_id,
            action_type=request.action.type,
            tool=request.action.tool,
            request_hash=request_hash,
            decision=decision.value,
            reasons_json=reasons_json,
            policy_trace_json=policy_trace_json,
            result_hash=result_hash_value,
            previous_record_hash=previous_record_hash,
            created_at=created_at,
        )

        # Sign the record hash
        gateway_signature = sign_record_hash(record_hash)

        # Create the record
        record = InteractionRecord(
            record_id=interaction_id,
            org_id=org_id,
            uapk_id=request.uapk_id,
            agent_id=request.agent_id,
            action_type=request.action.type,
            tool=request.action.tool,
            request=request_data,
            request_hash=request_hash,
            decision=decision,
            decision_reason=policy_result.reasons[0].message if policy_result.reasons else None,
            reasons_json=reasons_json,
            policy_trace_json=policy_trace_json,
            risk_snapshot_json=risk_snapshot_json,
            result=result_dict,
            result_hash=result_hash_value,
            duration_ms=tool_result.duration_ms if tool_result else None,
            previous_record_hash=previous_record_hash,
            record_hash=record_hash,
            gateway_signature=gateway_signature,
            created_at=created_at,
        )

        self.db.add(record)
        await self.db.commit()

        logger.info(
            "interaction_record_created",
            record_id=interaction_id,
            org_id=str(org_id),
            uapk_id=request.uapk_id,
            record_hash=record_hash[:16] + "...",
            previous_hash=previous_record_hash[:16] + "..." if previous_record_hash else None,
        )

        return record

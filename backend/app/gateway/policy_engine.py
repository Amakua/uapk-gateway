"""Policy Engine v0.1 - Deterministic policy evaluation for gateway actions."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capability_jwt import CapabilityTokenClaims, verify_capability_token
from app.core.config import get_settings
from app.core.ed25519 import public_key_from_base64
from app.core.logging import get_logger
from app.models.action_counter import ActionCounter
from app.models.capability_issuer import CapabilityIssuer, IssuerStatus
from app.models.uapk_manifest import ManifestStatus, UapkManifest
from app.schemas.gateway import (
    ActionInfo,
    CounterpartyInfo,
    GatewayDecision,
    ReasonCode,
    ReasonDetail,
)

logger = get_logger("gateway.policy_engine")


@dataclass
class PolicyContext:
    """Context for policy evaluation."""

    org_id: UUID
    uapk_id: str
    agent_id: str
    action: ActionInfo
    counterparty: CounterpartyInfo | None
    capability_token: str | None = None
    manifest: UapkManifest | None = None
    token_claims: CapabilityTokenClaims | None = None


@dataclass
class PolicyResult:
    """Result of policy evaluation."""

    decision: GatewayDecision
    reasons: list[ReasonDetail] = field(default_factory=list)
    manifest: UapkManifest | None = None
    budget_count: int = 0
    budget_limit: int = 0
    policy_trace: list[dict] = field(default_factory=list)
    risk_indicators: dict[str, Any] = field(default_factory=dict)

    def add_reason(
        self,
        code: ReasonCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add a reason to the result."""
        self.reasons.append(ReasonDetail(code=code, message=message, details=details))

    def add_trace(
        self,
        check_name: str,
        result: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add a check to the policy trace."""
        self.policy_trace.append({
            "check": check_name,
            "result": result,
            "details": details or {},
        })


class PolicyEngine:
    """Deterministic policy engine for gateway actions.

    Performs the following checks:
    1. Manifest exists and is active
    2. Action type is allowed for agent role
    3. Tool is allowed for agent role
    4. Amount caps (if params contain amount fields)
    5. Jurisdiction allowlist
    6. Counterparty allowlist/denylist
    7. Daily budget cap
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    async def evaluate(self, context: PolicyContext) -> PolicyResult:
        """Evaluate policies for an action request.

        Validates both manifest AND capability token constraints.
        The effective permissions are the intersection of both.

        Returns PolicyResult with decision, reasons, and policy trace.
        """
        result = PolicyResult(decision=GatewayDecision.ALLOW)

        # 1. Check manifest exists and is active
        manifest = await self._get_manifest(context.org_id, context.uapk_id)
        if manifest is None:
            result.decision = GatewayDecision.DENY
            result.add_reason(
                ReasonCode.MANIFEST_NOT_FOUND,
                f"No manifest found for uapk_id: {context.uapk_id}",
            )
            result.add_trace("manifest_lookup", "fail", {"uapk_id": context.uapk_id})
            return result

        if manifest.status != ManifestStatus.ACTIVE:
            result.decision = GatewayDecision.DENY
            result.add_reason(
                ReasonCode.MANIFEST_NOT_ACTIVE,
                f"Manifest is not active (status: {manifest.status.value})",
            )
            result.add_trace("manifest_status", "fail", {"status": manifest.status.value})
            return result

        result.manifest = manifest
        context.manifest = manifest
        result.add_trace("manifest_validation", "pass", {"manifest_id": str(manifest.id)})

        # 2. Validate capability token if provided
        if context.capability_token:
            token_valid = await self._validate_capability_token(context, result)
            if not token_valid:
                result.decision = GatewayDecision.DENY
                result.add_trace("capability_token_validation", "fail")
                return result
            result.add_trace("capability_token_validation", "pass", {
                "issuer": context.token_claims.iss if context.token_claims else None
            })
        else:
            result.add_trace("capability_token_validation", "skip", {"reason": "no_token_provided"})

        # Extract policy config from manifest
        manifest_json = manifest.manifest_json
        constraints = manifest_json.get("constraints", {})
        policy_config = manifest_json.get("policy", {})

        # 3. Check action type allowed (manifest)
        if not self._check_action_type_allowed(context, policy_config, result):
            result.decision = GatewayDecision.DENY
            result.add_trace("manifest_action_type", "fail", {"action_type": context.action.type})
            return result
        result.add_trace("manifest_action_type", "pass", {"action_type": context.action.type})

        # 4. Check action type allowed (capability token)
        if context.token_claims:
            if not self._check_token_action_type_allowed(context, result):
                result.decision = GatewayDecision.DENY
                result.add_trace("token_action_type", "fail", {"action_type": context.action.type})
                return result
            result.add_trace("token_action_type", "pass")
        else:
            result.add_trace("token_action_type", "skip")

        # 5. Check tool allowed (manifest)
        if not self._check_tool_allowed(context, policy_config, result):
            result.decision = GatewayDecision.DENY
            result.add_trace("manifest_tool", "fail", {"tool": context.action.tool})
            return result
        result.add_trace("manifest_tool", "pass", {"tool": context.action.tool})

        # 6. Check tool allowed (capability token)
        if context.token_claims:
            if not self._check_token_tool_allowed(context, result):
                result.decision = GatewayDecision.DENY
                result.add_trace("token_tool", "fail", {"tool": context.action.tool})
                return result
            result.add_trace("token_tool", "pass")
        else:
            result.add_trace("token_tool", "skip")

        # 7. Check amount caps (manifest)
        amount_result = self._check_amount_caps(context, policy_config, result)
        if amount_result == GatewayDecision.DENY:
            result.decision = GatewayDecision.DENY
            result.add_trace("manifest_amount_cap", "fail")
            return result
        elif amount_result == GatewayDecision.ESCALATE:
            result.decision = GatewayDecision.ESCALATE
            result.add_trace("manifest_amount_cap", "escalate")
        else:
            result.add_trace("manifest_amount_cap", "pass")

        # 8. Check amount caps (capability token)
        if context.token_claims:
            token_amount_result = self._check_token_amount_caps(context, result)
            if token_amount_result == GatewayDecision.DENY:
                result.decision = GatewayDecision.DENY
                result.add_trace("token_amount_cap", "fail")
                return result
            result.add_trace("token_amount_cap", "pass")
        else:
            result.add_trace("token_amount_cap", "skip")

        # 9. Check jurisdiction allowlist (manifest)
        if not self._check_jurisdiction(context, policy_config, result):
            result.decision = GatewayDecision.DENY
            result.add_trace("manifest_jurisdiction", "fail")
            return result
        result.add_trace("manifest_jurisdiction", "pass")

        # 10. Check jurisdiction allowlist (capability token)
        if context.token_claims:
            if not self._check_token_jurisdiction(context, result):
                result.decision = GatewayDecision.DENY
                result.add_trace("token_jurisdiction", "fail")
                return result
            result.add_trace("token_jurisdiction", "pass")
        else:
            result.add_trace("token_jurisdiction", "skip")

        # 11. Check counterparty allowlist/denylist (manifest)
        if not self._check_counterparty(context, policy_config, result):
            result.decision = GatewayDecision.DENY
            result.add_trace("manifest_counterparty", "fail")
            return result
        result.add_trace("manifest_counterparty", "pass")

        # 12. Check counterparty allowlist/denylist (capability token)
        if context.token_claims:
            if not self._check_token_counterparty(context, result):
                result.decision = GatewayDecision.DENY
                result.add_trace("token_counterparty", "fail")
                return result
            result.add_trace("token_counterparty", "pass")
        else:
            result.add_trace("token_counterparty", "skip")

        # 13. Check daily budget
        budget_result = await self._check_budget(context, constraints, result)
        if budget_result == GatewayDecision.DENY:
            result.decision = GatewayDecision.DENY
            result.add_trace("budget_check", "fail", {
                "count": result.budget_count,
                "limit": result.budget_limit,
            })
            return result
        elif budget_result == GatewayDecision.ESCALATE and result.decision != GatewayDecision.ESCALATE:
            result.decision = GatewayDecision.ESCALATE
            result.add_trace("budget_check", "escalate", {
                "count": result.budget_count,
                "limit": result.budget_limit,
            })
        else:
            result.add_trace("budget_check", "pass", {
                "count": result.budget_count,
                "limit": result.budget_limit,
            })

        # Store risk indicators
        result.risk_indicators["budget_current"] = result.budget_count
        result.risk_indicators["budget_limit"] = result.budget_limit

        # If we get here with ALLOW, add success reason
        if result.decision == GatewayDecision.ALLOW:
            result.add_reason(
                ReasonCode.ALL_CHECKS_PASSED,
                "All policy checks passed",
            )

        return result

    async def _get_manifest(self, org_id: UUID, uapk_id: str) -> UapkManifest | None:
        """Get the active manifest for a UAPK ID."""
        result = await self.db.execute(
            select(UapkManifest)
            .where(
                UapkManifest.org_id == org_id,
                UapkManifest.uapk_id == uapk_id,
            )
            .order_by(UapkManifest.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _check_action_type_allowed(
        self,
        context: PolicyContext,
        policy_config: dict,
        result: PolicyResult,
    ) -> bool:
        """Check if the action type is allowed."""
        allowed_action_types = policy_config.get("allowed_action_types", [])

        # If no restriction, allow all
        if not allowed_action_types:
            return True

        if context.action.type not in allowed_action_types:
            result.add_reason(
                ReasonCode.ACTION_TYPE_NOT_ALLOWED,
                f"Action type '{context.action.type}' is not allowed",
                {"allowed_types": allowed_action_types},
            )
            return False

        return True

    def _check_tool_allowed(
        self,
        context: PolicyContext,
        policy_config: dict,
        result: PolicyResult,
    ) -> bool:
        """Check if the tool is allowed."""
        allowed_tools = policy_config.get("allowed_tools", [])
        denied_tools = policy_config.get("denied_tools", [])

        # Check denylist first
        if context.action.tool in denied_tools:
            result.add_reason(
                ReasonCode.TOOL_NOT_ALLOWED,
                f"Tool '{context.action.tool}' is explicitly denied",
            )
            return False

        # If allowlist is specified, check it
        if allowed_tools and context.action.tool not in allowed_tools:
            result.add_reason(
                ReasonCode.TOOL_NOT_ALLOWED,
                f"Tool '{context.action.tool}' is not in allowed tools list",
                {"allowed_tools": allowed_tools},
            )
            return False

        return True

    def _check_amount_caps(
        self,
        context: PolicyContext,
        policy_config: dict,
        result: PolicyResult,
    ) -> GatewayDecision:
        """Check amount caps on parameters.

        Returns ALLOW, DENY, or ESCALATE.
        """
        amount_caps = policy_config.get("amount_caps", {})
        if not amount_caps:
            return GatewayDecision.ALLOW

        # Get configurable param paths (default to common ones)
        amount_param_paths = amount_caps.get("param_paths", ["amount", "value", "total"])
        max_amount = amount_caps.get("max_amount")
        escalate_amount = amount_caps.get("escalate_above")
        currency_field = amount_caps.get("currency_field", "currency")

        # Extract amount from params
        amount = None
        for path in amount_param_paths:
            amount = self._get_nested_value(context.action.params, path)
            if amount is not None:
                break

        if amount is None:
            return GatewayDecision.ALLOW

        # Try to convert to float
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return GatewayDecision.ALLOW

        # Check hard cap
        if max_amount is not None and amount > max_amount:
            result.add_reason(
                ReasonCode.AMOUNT_EXCEEDS_CAP,
                f"Amount {amount} exceeds maximum allowed {max_amount}",
                {"amount": amount, "max_amount": max_amount},
            )
            return GatewayDecision.DENY

        # Check escalation threshold
        if escalate_amount is not None and amount > escalate_amount:
            result.add_reason(
                ReasonCode.AMOUNT_REQUIRES_APPROVAL,
                f"Amount {amount} exceeds threshold {escalate_amount}, requires approval",
                {"amount": amount, "escalate_above": escalate_amount},
            )
            return GatewayDecision.ESCALATE

        return GatewayDecision.ALLOW

    def _check_jurisdiction(
        self,
        context: PolicyContext,
        policy_config: dict,
        result: PolicyResult,
    ) -> bool:
        """Check jurisdiction allowlist."""
        allowed_jurisdictions = policy_config.get("allowed_jurisdictions", [])

        if not allowed_jurisdictions:
            return True

        if context.counterparty is None or context.counterparty.jurisdiction is None:
            # If no jurisdiction info, allow by default (could be configured)
            return True

        jurisdiction = context.counterparty.jurisdiction.upper()
        allowed_upper = [j.upper() for j in allowed_jurisdictions]

        if jurisdiction not in allowed_upper:
            result.add_reason(
                ReasonCode.JURISDICTION_NOT_ALLOWED,
                f"Jurisdiction '{jurisdiction}' is not in allowed list",
                {"allowed_jurisdictions": allowed_jurisdictions},
            )
            return False

        return True

    def _check_counterparty(
        self,
        context: PolicyContext,
        policy_config: dict,
        result: PolicyResult,
    ) -> bool:
        """Check counterparty allowlist/denylist."""
        counterparty_rules = policy_config.get("counterparty", {})

        if not counterparty_rules or context.counterparty is None:
            return True

        cp_id = context.counterparty.id
        if cp_id is None:
            return True

        # Check denylist first
        denylist = counterparty_rules.get("denylist", [])
        if cp_id in denylist:
            result.add_reason(
                ReasonCode.COUNTERPARTY_DENIED,
                f"Counterparty '{cp_id}' is in denylist",
            )
            return False

        # Check allowlist if specified
        allowlist = counterparty_rules.get("allowlist", [])
        if allowlist and cp_id not in allowlist:
            result.add_reason(
                ReasonCode.COUNTERPARTY_NOT_IN_ALLOWLIST,
                f"Counterparty '{cp_id}' is not in allowlist",
            )
            return False

        return True

    async def _check_budget(
        self,
        context: PolicyContext,
        constraints: dict,
        result: PolicyResult,
    ) -> GatewayDecision:
        """Check daily budget cap."""
        # Get budget limit from constraints or use default
        daily_cap = constraints.get(
            "max_actions_per_day",
            self.settings.gateway_default_daily_budget,
        )
        escalate_at_percent = constraints.get("budget_escalate_at_percent", 90)

        # Get or create counter
        today = date.today()
        counter = await self._get_or_create_counter(context.org_id, context.uapk_id, today)

        result.budget_count = counter.count
        result.budget_limit = daily_cap

        # Check if exceeded
        if counter.count >= daily_cap:
            result.add_reason(
                ReasonCode.BUDGET_EXCEEDED,
                f"Daily action budget exceeded ({counter.count}/{daily_cap})",
                {"current_count": counter.count, "daily_cap": daily_cap},
            )
            return GatewayDecision.DENY

        # Check if nearing threshold (escalate)
        threshold = int(daily_cap * escalate_at_percent / 100)
        if counter.count >= threshold:
            result.add_reason(
                ReasonCode.BUDGET_THRESHOLD_REACHED,
                f"Approaching daily budget limit ({counter.count}/{daily_cap})",
                {"current_count": counter.count, "daily_cap": daily_cap, "threshold_percent": escalate_at_percent},
            )
            return GatewayDecision.ESCALATE

        return GatewayDecision.ALLOW

    async def _get_or_create_counter(
        self,
        org_id: UUID,
        uapk_id: str,
        counter_date: date,
    ) -> ActionCounter:
        """Get or create an action counter for today."""
        # Try to get existing counter
        result = await self.db.execute(
            select(ActionCounter).where(
                ActionCounter.org_id == org_id,
                ActionCounter.uapk_id == uapk_id,
                ActionCounter.counter_date == counter_date,
            )
        )
        counter = result.scalar_one_or_none()

        if counter is not None:
            return counter

        # Create new counter
        counter = ActionCounter(
            org_id=org_id,
            uapk_id=uapk_id,
            counter_date=counter_date,
            count=0,
        )
        self.db.add(counter)
        await self.db.flush()
        return counter

    async def increment_budget(
        self,
        org_id: UUID,
        uapk_id: str,
    ) -> int:
        """Atomically increment the action counter for today.

        Returns the new count.
        """
        today = date.today()

        # Use upsert with atomic increment
        stmt = insert(ActionCounter).values(
            org_id=org_id,
            uapk_id=uapk_id,
            counter_date=today,
            count=1,
            updated_at=datetime.now(UTC),
        ).on_conflict_do_update(
            constraint="uq_action_counter_org_uapk_date",
            set_={"count": ActionCounter.count + 1, "updated_at": datetime.now(UTC)},
        ).returning(ActionCounter.count)

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one()

    def _get_nested_value(self, data: dict, path: str) -> Any:
        """Get a nested value from a dict using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            if value is None:
                return None
        return value

    # =========================================================================
    # Capability Token Validation Methods
    # =========================================================================

    async def _validate_capability_token(
        self,
        context: PolicyContext,
        result: PolicyResult,
    ) -> bool:
        """Validate capability token signature, issuer, and basic claims.

        Returns True if token is valid, False otherwise.
        """
        if not context.capability_token:
            return True  # No token provided is OK

        # Get issuer public keys for this org
        issuer_keys = await self._get_issuer_public_keys(context.org_id)

        # Verify token signature and decode claims
        claims, error = verify_capability_token(
            context.capability_token,
            issuer_public_keys=issuer_keys,
        )

        if error:
            logger.warning(
                "capability_token_invalid",
                org_id=str(context.org_id),
                agent_id=context.agent_id,
                error=error,
            )
            result.add_reason(
                ReasonCode.CAPABILITY_TOKEN_INVALID,
                f"Invalid capability token: {error}",
            )
            return False

        # Store claims in context for later checks
        context.token_claims = claims

        # Verify token is for this org
        if claims.org_id != str(context.org_id):
            result.add_reason(
                ReasonCode.TOKEN_ORG_MISMATCH,
                f"Token org_id '{claims.org_id}' does not match request org_id",
            )
            return False

        # Verify token is for this UAPK
        if claims.uapk_id != context.uapk_id:
            result.add_reason(
                ReasonCode.TOKEN_UAPK_MISMATCH,
                f"Token uapk_id '{claims.uapk_id}' does not match request uapk_id",
            )
            return False

        # Verify token is for this agent
        if claims.sub != context.agent_id:
            result.add_reason(
                ReasonCode.TOKEN_AGENT_MISMATCH,
                f"Token subject '{claims.sub}' does not match agent_id",
            )
            return False

        # Verify issuer is active (not revoked)
        if claims.iss != "gateway":
            issuer_active = await self._check_issuer_active(context.org_id, claims.iss)
            if not issuer_active:
                result.add_reason(
                    ReasonCode.TOKEN_ISSUER_REVOKED,
                    f"Token issuer '{claims.iss}' has been revoked",
                )
                return False

        logger.info(
            "capability_token_validated",
            org_id=str(context.org_id),
            agent_id=context.agent_id,
            issuer_id=claims.iss,
            token_id=claims.jti,
        )

        return True

    async def _get_issuer_public_keys(
        self,
        org_id: UUID,
    ) -> dict[str, Ed25519PublicKey]:
        """Get all active issuer public keys for an organization.

        Returns dict of issuer_id -> Ed25519PublicKey
        """
        from app.core.ed25519 import get_gateway_key_manager

        result = await self.db.execute(
            select(CapabilityIssuer).where(
                CapabilityIssuer.org_id == org_id,
                CapabilityIssuer.status == IssuerStatus.ACTIVE,
            )
        )
        issuers = result.scalars().all()

        keys: dict[str, Ed25519PublicKey] = {}

        # Add gateway key
        key_manager = get_gateway_key_manager()
        keys["gateway"] = key_manager.public_key

        # Add org-specific issuers
        for issuer in issuers:
            try:
                public_key = public_key_from_base64(issuer.public_key)
                keys[issuer.issuer_id] = public_key
            except Exception as e:
                logger.warning(
                    "invalid_issuer_public_key",
                    issuer_id=issuer.issuer_id,
                    error=str(e),
                )

        return keys

    async def _check_issuer_active(
        self,
        org_id: UUID,
        issuer_id: str,
    ) -> bool:
        """Check if an issuer is active (not revoked)."""
        if issuer_id == "gateway":
            return True

        result = await self.db.execute(
            select(CapabilityIssuer).where(
                CapabilityIssuer.org_id == org_id,
                CapabilityIssuer.issuer_id == issuer_id,
                CapabilityIssuer.status == IssuerStatus.ACTIVE,
            )
        )
        issuer = result.scalar_one_or_none()
        return issuer is not None

    def _check_token_action_type_allowed(
        self,
        context: PolicyContext,
        result: PolicyResult,
    ) -> bool:
        """Check if action type is allowed by capability token."""
        if not context.token_claims:
            return True

        allowed_types = context.token_claims.allowed_action_types

        # If no restriction in token, allow all
        if not allowed_types:
            return True

        if context.action.type not in allowed_types:
            result.add_reason(
                ReasonCode.TOKEN_ACTION_TYPE_NOT_ALLOWED,
                f"Action type '{context.action.type}' not allowed by capability token",
                {"token_allowed_types": allowed_types},
            )
            return False

        return True

    def _check_token_tool_allowed(
        self,
        context: PolicyContext,
        result: PolicyResult,
    ) -> bool:
        """Check if tool is allowed by capability token."""
        if not context.token_claims:
            return True

        allowed_tools = context.token_claims.allowed_tools

        # If no restriction in token, allow all
        if not allowed_tools:
            return True

        if context.action.tool not in allowed_tools:
            result.add_reason(
                ReasonCode.TOKEN_TOOL_NOT_ALLOWED,
                f"Tool '{context.action.tool}' not allowed by capability token",
                {"token_allowed_tools": allowed_tools},
            )
            return False

        return True

    def _check_token_amount_caps(
        self,
        context: PolicyContext,
        result: PolicyResult,
    ) -> GatewayDecision:
        """Check amount caps from capability token constraints."""
        if not context.token_claims or not context.token_claims.constraints:
            return GatewayDecision.ALLOW

        constraints = context.token_claims.constraints
        if constraints.amount_max is None:
            return GatewayDecision.ALLOW

        # Get configurable param paths
        amount_param_paths = ["amount", "value", "total"]

        # Extract amount from params
        amount = None
        for path in amount_param_paths:
            amount = self._get_nested_value(context.action.params, path)
            if amount is not None:
                break

        if amount is None:
            return GatewayDecision.ALLOW

        # Try to convert to float
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return GatewayDecision.ALLOW

        # Check against token cap
        if amount > constraints.amount_max:
            result.add_reason(
                ReasonCode.TOKEN_AMOUNT_EXCEEDS_CAP,
                f"Amount {amount} exceeds token cap {constraints.amount_max}",
                {"amount": amount, "token_max_amount": constraints.amount_max},
            )
            return GatewayDecision.DENY

        return GatewayDecision.ALLOW

    def _check_token_jurisdiction(
        self,
        context: PolicyContext,
        result: PolicyResult,
    ) -> bool:
        """Check jurisdiction against capability token constraints."""
        if not context.token_claims or not context.token_claims.constraints:
            return True

        allowed_jurisdictions = context.token_claims.constraints.jurisdictions
        if not allowed_jurisdictions:
            return True

        if context.counterparty is None or context.counterparty.jurisdiction is None:
            return True

        jurisdiction = context.counterparty.jurisdiction.upper()
        allowed_upper = [j.upper() for j in allowed_jurisdictions]

        if jurisdiction not in allowed_upper:
            result.add_reason(
                ReasonCode.TOKEN_JURISDICTION_NOT_ALLOWED,
                f"Jurisdiction '{jurisdiction}' not allowed by capability token",
                {"token_allowed_jurisdictions": allowed_jurisdictions},
            )
            return False

        return True

    def _check_token_counterparty(
        self,
        context: PolicyContext,
        result: PolicyResult,
    ) -> bool:
        """Check counterparty against capability token constraints."""
        if not context.token_claims or not context.token_claims.constraints:
            return True

        if context.counterparty is None or context.counterparty.id is None:
            return True

        constraints = context.token_claims.constraints
        cp_id = context.counterparty.id

        # Check denylist
        if constraints.counterparty_denylist and cp_id in constraints.counterparty_denylist:
            result.add_reason(
                ReasonCode.TOKEN_COUNTERPARTY_NOT_ALLOWED,
                f"Counterparty '{cp_id}' denied by capability token",
            )
            return False

        # Check allowlist
        if constraints.counterparty_allowlist and cp_id not in constraints.counterparty_allowlist:
            result.add_reason(
                ReasonCode.TOKEN_COUNTERPARTY_NOT_ALLOWED,
                f"Counterparty '{cp_id}' not in token allowlist",
            )
            return False

        return True

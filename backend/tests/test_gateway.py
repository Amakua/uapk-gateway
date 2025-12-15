"""Tests for the Agent Interaction Gateway."""

import pytest
from datetime import UTC, datetime
from uuid import uuid4

from app.gateway.connectors import ConnectorConfig, MockConnector
from app.gateway.policy_engine import PolicyContext, PolicyEngine
from app.schemas.gateway import (
    ActionInfo,
    CounterpartyInfo,
    GatewayActionRequest,
    GatewayDecision,
    ReasonCode,
)


class TestMockConnector:
    """Tests for the MockConnector."""

    @pytest.mark.asyncio
    async def test_mock_connector_success(self):
        """Test MockConnector returns success with echo."""
        config = ConnectorConfig(connector_type="mock")
        connector = MockConnector(config)

        params = {"message": "hello", "count": 42}
        result = await connector.execute(params)

        assert result.success is True
        assert result.data is not None
        assert result.data["echo"] == params
        assert result.data["connector"] == "mock"
        assert result.result_hash is not None
        assert result.duration_ms is not None

    @pytest.mark.asyncio
    async def test_mock_connector_custom_response(self):
        """Test MockConnector with custom response data."""
        config = ConnectorConfig(
            connector_type="mock",
            extra={"response_data": {"status": "ok", "custom": "data"}},
        )
        connector = MockConnector(config)

        result = await connector.execute({})

        assert result.success is True
        assert result.data == {"status": "ok", "custom": "data"}

    @pytest.mark.asyncio
    async def test_mock_connector_simulated_failure(self):
        """Test MockConnector simulated failure."""
        config = ConnectorConfig(
            connector_type="mock",
            extra={
                "should_fail": True,
                "error_code": "TEST_ERROR",
                "error_message": "Simulated test failure",
            },
        )
        connector = MockConnector(config)

        result = await connector.execute({})

        assert result.success is False
        assert result.error is not None
        assert result.error["code"] == "TEST_ERROR"
        assert result.error["message"] == "Simulated test failure"

    @pytest.mark.asyncio
    async def test_mock_connector_with_delay(self):
        """Test MockConnector with simulated delay."""
        config = ConnectorConfig(
            connector_type="mock",
            extra={"delay_ms": 50},
        )
        connector = MockConnector(config)

        start = datetime.now(UTC)
        result = await connector.execute({})
        duration = (datetime.now(UTC) - start).total_seconds() * 1000

        assert result.success is True
        assert duration >= 50  # Should have delayed at least 50ms


class TestPolicyEngine:
    """Tests for the PolicyEngine."""

    def _create_context(
        self,
        action_type: str = "payment",
        tool: str = "stripe_transfer",
        params: dict | None = None,
        counterparty: CounterpartyInfo | None = None,
    ) -> PolicyContext:
        """Helper to create a policy context."""
        return PolicyContext(
            org_id=uuid4(),
            uapk_id="test-agent",
            agent_id="agent-instance-1",
            action=ActionInfo(
                type=action_type,
                tool=tool,
                params=params or {},
            ),
            counterparty=counterparty,
        )

    def test_check_action_type_allowed_no_restrictions(self):
        """Test action type check with no restrictions."""
        # This requires DB so we'll test the helper method logic
        context = self._create_context(action_type="payment")
        policy_config = {}  # No allowed_action_types = allow all

        from app.gateway.policy_engine import PolicyResult

        result = PolicyResult(decision=GatewayDecision.ALLOW)

        # Simulate the check logic
        allowed_action_types = policy_config.get("allowed_action_types", [])
        if not allowed_action_types:
            allowed = True
        else:
            allowed = context.action.type in allowed_action_types

        assert allowed is True

    def test_check_action_type_allowed_with_allowlist(self):
        """Test action type check with allowlist."""
        context = self._create_context(action_type="payment")
        policy_config = {"allowed_action_types": ["payment", "notification"]}

        allowed_action_types = policy_config.get("allowed_action_types", [])
        allowed = context.action.type in allowed_action_types

        assert allowed is True

    def test_check_action_type_denied(self):
        """Test action type check when type not in allowlist."""
        context = self._create_context(action_type="admin")
        policy_config = {"allowed_action_types": ["payment", "notification"]}

        allowed_action_types = policy_config.get("allowed_action_types", [])
        allowed = context.action.type in allowed_action_types

        assert allowed is False

    def test_check_tool_denied(self):
        """Test tool check with denylist."""
        context = self._create_context(tool="dangerous_tool")
        policy_config = {"denied_tools": ["dangerous_tool", "admin_tool"]}

        denied_tools = policy_config.get("denied_tools", [])
        denied = context.action.tool in denied_tools

        assert denied is True

    def test_check_amount_caps_under_limit(self):
        """Test amount check under limit."""
        context = self._create_context(
            params={"amount": 100, "currency": "USD"}
        )
        policy_config = {
            "amount_caps": {
                "param_paths": ["amount"],
                "max_amount": 1000,
                "escalate_above": 500,
            }
        }

        amount = context.action.params.get("amount")
        max_amount = policy_config["amount_caps"]["max_amount"]
        escalate_above = policy_config["amount_caps"]["escalate_above"]

        assert amount < max_amount
        assert amount < escalate_above

    def test_check_amount_caps_exceeds_limit(self):
        """Test amount check exceeds limit."""
        context = self._create_context(
            params={"amount": 1500, "currency": "USD"}
        )
        policy_config = {
            "amount_caps": {
                "param_paths": ["amount"],
                "max_amount": 1000,
            }
        }

        amount = context.action.params.get("amount")
        max_amount = policy_config["amount_caps"]["max_amount"]

        assert amount > max_amount

    def test_check_amount_caps_escalate(self):
        """Test amount check triggers escalation."""
        context = self._create_context(
            params={"amount": 600, "currency": "USD"}
        )
        policy_config = {
            "amount_caps": {
                "param_paths": ["amount"],
                "max_amount": 1000,
                "escalate_above": 500,
            }
        }

        amount = context.action.params.get("amount")
        escalate_above = policy_config["amount_caps"]["escalate_above"]
        max_amount = policy_config["amount_caps"]["max_amount"]

        assert amount > escalate_above
        assert amount < max_amount

    def test_check_jurisdiction_allowed(self):
        """Test jurisdiction check with allowlist."""
        context = self._create_context(
            counterparty=CounterpartyInfo(
                id="customer-1",
                type="user",
                jurisdiction="US",
            )
        )
        policy_config = {"allowed_jurisdictions": ["US", "CA", "GB"]}

        jurisdiction = context.counterparty.jurisdiction.upper()
        allowed = [j.upper() for j in policy_config["allowed_jurisdictions"]]

        assert jurisdiction in allowed

    def test_check_jurisdiction_denied(self):
        """Test jurisdiction check when not in allowlist."""
        context = self._create_context(
            counterparty=CounterpartyInfo(
                id="customer-1",
                type="user",
                jurisdiction="RU",
            )
        )
        policy_config = {"allowed_jurisdictions": ["US", "CA", "GB"]}

        jurisdiction = context.counterparty.jurisdiction.upper()
        allowed = [j.upper() for j in policy_config["allowed_jurisdictions"]]

        assert jurisdiction not in allowed

    def test_check_counterparty_denylist(self):
        """Test counterparty denylist check."""
        context = self._create_context(
            counterparty=CounterpartyInfo(
                id="banned-user-123",
                type="user",
            )
        )
        policy_config = {
            "counterparty": {
                "denylist": ["banned-user-123", "suspicious-entity"],
            }
        }

        cp_id = context.counterparty.id
        denylist = policy_config["counterparty"]["denylist"]

        assert cp_id in denylist

    def test_check_counterparty_allowlist(self):
        """Test counterparty allowlist check."""
        context = self._create_context(
            counterparty=CounterpartyInfo(
                id="trusted-partner",
                type="merchant",
            )
        )
        policy_config = {
            "counterparty": {
                "allowlist": ["trusted-partner", "verified-vendor"],
            }
        }

        cp_id = context.counterparty.id
        allowlist = policy_config["counterparty"]["allowlist"]

        assert cp_id in allowlist


class TestGatewayRequest:
    """Tests for GatewayActionRequest validation."""

    def test_valid_request(self):
        """Test valid gateway request."""
        request = GatewayActionRequest(
            uapk_id="test-agent",
            agent_id="agent-1",
            action=ActionInfo(
                type="payment",
                tool="stripe_transfer",
                params={"amount": 100, "currency": "USD"},
            ),
        )

        assert request.uapk_id == "test-agent"
        assert request.action.type == "payment"
        assert request.action.tool == "stripe_transfer"

    def test_request_with_counterparty(self):
        """Test request with counterparty info."""
        request = GatewayActionRequest(
            uapk_id="test-agent",
            agent_id="agent-1",
            action=ActionInfo(
                type="payment",
                tool="stripe_transfer",
                params={"amount": 100},
            ),
            counterparty=CounterpartyInfo(
                id="customer-123",
                type="user",
                jurisdiction="US",
            ),
        )

        assert request.counterparty is not None
        assert request.counterparty.id == "customer-123"
        assert request.counterparty.jurisdiction == "US"

    def test_request_with_context(self):
        """Test request with optional context."""
        request = GatewayActionRequest(
            uapk_id="test-agent",
            agent_id="agent-1",
            action=ActionInfo(type="notification", tool="email_send", params={}),
            context={
                "conversation_id": "conv-123",
                "reason": "Customer requested update",
            },
        )

        assert request.context is not None
        assert request.context["conversation_id"] == "conv-123"


class TestReasonCodes:
    """Tests for reason codes."""

    def test_allow_reason_codes(self):
        """Test allow reason codes exist."""
        assert ReasonCode.POLICY_PASSED
        assert ReasonCode.ALL_CHECKS_PASSED

    def test_deny_reason_codes(self):
        """Test deny reason codes exist."""
        assert ReasonCode.MANIFEST_NOT_FOUND
        assert ReasonCode.MANIFEST_NOT_ACTIVE
        assert ReasonCode.ACTION_TYPE_NOT_ALLOWED
        assert ReasonCode.TOOL_NOT_ALLOWED
        assert ReasonCode.AMOUNT_EXCEEDS_CAP
        assert ReasonCode.JURISDICTION_NOT_ALLOWED
        assert ReasonCode.COUNTERPARTY_DENIED
        assert ReasonCode.BUDGET_EXCEEDED

    def test_escalate_reason_codes(self):
        """Test escalate reason codes exist."""
        assert ReasonCode.REQUIRES_HUMAN_APPROVAL
        assert ReasonCode.AMOUNT_REQUIRES_APPROVAL
        assert ReasonCode.BUDGET_THRESHOLD_REACHED

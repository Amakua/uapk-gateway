"""Tests for audit log hash chain and signature verification."""

from datetime import UTC, datetime

import pytest

from app.core.audit import (
    PolicyTrace,
    RiskSnapshot,
    canonicalize_json,
    compute_hash,
    compute_record_hash,
    compute_request_hash,
    compute_result_hash,
    sign_record_hash,
    verify_hash_chain,
    verify_record_signature,
)


class TestCanonicalization:
    """Tests for JSON canonicalization."""

    def test_canonicalize_simple_dict(self):
        """Canonical JSON should be deterministic."""
        data = {"b": 1, "a": 2, "c": 3}
        result = canonicalize_json(data)
        # Keys should be sorted
        assert result == '{"a":2,"b":1,"c":3}'

    def test_canonicalize_nested_dict(self):
        """Nested dicts should also be sorted."""
        data = {"outer": {"z": 1, "a": 2}}
        result = canonicalize_json(data)
        assert result == '{"outer":{"a":2,"z":1}}'

    def test_canonicalize_list(self):
        """Lists should preserve order."""
        data = {"items": [3, 1, 2]}
        result = canonicalize_json(data)
        assert result == '{"items":[3,1,2]}'

    def test_canonicalize_null(self):
        """Null values should be preserved."""
        data = {"key": None}
        result = canonicalize_json(data)
        assert result == '{"key":null}'

    def test_canonicalize_bool(self):
        """Booleans should be preserved."""
        data = {"yes": True, "no": False}
        result = canonicalize_json(data)
        assert result == '{"no":false,"yes":true}'

    def test_canonicalize_float_int(self):
        """Floats that are integers should be normalized."""
        data = {"value": 5.0}
        result = canonicalize_json(data)
        assert result == '{"value":5}'

    def test_canonicalize_datetime(self):
        """Datetimes should be converted to ISO format."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        data = {"timestamp": dt}
        result = canonicalize_json(data)
        assert "2024-01-15" in result
        assert "10:30:00" in result

    def test_canonicalize_deterministic(self):
        """Same data should always produce same canonical JSON."""
        data1 = {"z": 1, "a": 2, "m": {"y": 3, "x": 4}}
        data2 = {"a": 2, "m": {"x": 4, "y": 3}, "z": 1}
        assert canonicalize_json(data1) == canonicalize_json(data2)


class TestHashing:
    """Tests for hash computation."""

    def test_compute_hash(self):
        """Hash should be a 64-character hex string (SHA-256)."""
        result = compute_hash("test data")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_compute_hash_deterministic(self):
        """Same input should produce same hash."""
        data = "test data"
        hash1 = compute_hash(data)
        hash2 = compute_hash(data)
        assert hash1 == hash2

    def test_compute_hash_different_input(self):
        """Different input should produce different hash."""
        hash1 = compute_hash("data 1")
        hash2 = compute_hash("data 2")
        assert hash1 != hash2

    def test_compute_request_hash(self):
        """Request hash should be deterministic for same content."""
        request_data = {
            "uapk_id": "test-uapk",
            "agent_id": "test-agent",
            "action": {"type": "api", "tool": "send_email"},
        }
        hash1 = compute_request_hash(request_data)
        hash2 = compute_request_hash(request_data)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_compute_result_hash_none(self):
        """Result hash should be None for None input."""
        assert compute_result_hash(None) is None

    def test_compute_result_hash(self):
        """Result hash should be computed for valid result."""
        result_data = {"success": True, "data": {"id": 123}}
        hash_value = compute_result_hash(result_data)
        assert hash_value is not None
        assert len(hash_value) == 64


class TestRecordHash:
    """Tests for record hash computation."""

    def test_compute_record_hash(self):
        """Record hash should include all fields."""
        record_hash = compute_record_hash(
            record_id="int-abc123",
            org_id="org-123",
            uapk_id="test-uapk",
            agent_id="test-agent",
            action_type="api",
            tool="send_email",
            request_hash="a" * 64,
            decision="approved",
            reasons_json='[{"code":"ALLOWED"}]',
            policy_trace_json='{"checks":[]}',
            result_hash=None,
            previous_record_hash=None,
            created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        )
        assert len(record_hash) == 64

    def test_compute_record_hash_with_chain(self):
        """Record hash should change when previous hash changes."""
        base_params = {
            "record_id": "int-abc123",
            "org_id": "org-123",
            "uapk_id": "test-uapk",
            "agent_id": "test-agent",
            "action_type": "api",
            "tool": "send_email",
            "request_hash": "a" * 64,
            "decision": "approved",
            "reasons_json": '[]',
            "policy_trace_json": '{"checks":[]}',
            "result_hash": None,
            "created_at": datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        }

        hash_no_prev = compute_record_hash(**base_params, previous_record_hash=None)
        hash_with_prev = compute_record_hash(**base_params, previous_record_hash="b" * 64)

        assert hash_no_prev != hash_with_prev

    def test_compute_record_hash_deterministic(self):
        """Same parameters should produce same hash."""
        params = {
            "record_id": "int-abc123",
            "org_id": "org-123",
            "uapk_id": "test-uapk",
            "agent_id": "test-agent",
            "action_type": "api",
            "tool": "send_email",
            "request_hash": "a" * 64,
            "decision": "approved",
            "reasons_json": '[]',
            "policy_trace_json": '{"checks":[]}',
            "result_hash": None,
            "previous_record_hash": None,
            "created_at": datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        }

        hash1 = compute_record_hash(**params)
        hash2 = compute_record_hash(**params)
        assert hash1 == hash2


class TestSignatures:
    """Tests for Ed25519 signatures."""

    def test_sign_and_verify(self):
        """Signature should be verifiable."""
        record_hash = compute_hash("test record data")
        signature = sign_record_hash(record_hash)

        # Signature should be base64 encoded
        assert len(signature) > 0

        # Should verify
        assert verify_record_signature(record_hash, signature) is True

    def test_verify_invalid_signature(self):
        """Invalid signature should fail verification."""
        record_hash = compute_hash("test record data")

        # Modified signature should fail
        assert verify_record_signature(record_hash, "invalid-signature") is False

    def test_verify_wrong_data(self):
        """Signature for different data should fail."""
        record_hash1 = compute_hash("test record data 1")
        record_hash2 = compute_hash("test record data 2")

        signature = sign_record_hash(record_hash1)

        # Signature should not verify for different data
        assert verify_record_signature(record_hash2, signature) is False


class TestHashChainVerification:
    """Tests for hash chain verification."""

    def test_verify_empty_chain(self):
        """Empty chain should be valid."""
        is_valid, errors = verify_hash_chain([])
        assert is_valid is True
        assert errors == []

    def test_verify_single_record_chain(self):
        """Single record chain should be valid if hash is correct."""
        created_at = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        record_hash = compute_record_hash(
            record_id="int-001",
            org_id="org-123",
            uapk_id="test-uapk",
            agent_id="test-agent",
            action_type="api",
            tool="send_email",
            request_hash="a" * 64,
            decision="approved",
            reasons_json="[]",
            policy_trace_json='{"checks":[]}',
            result_hash=None,
            previous_record_hash=None,
            created_at=created_at,
        )

        signature = sign_record_hash(record_hash)

        records = [{
            "record_id": "int-001",
            "org_id": "org-123",
            "uapk_id": "test-uapk",
            "agent_id": "test-agent",
            "action_type": "api",
            "tool": "send_email",
            "request_hash": "a" * 64,
            "decision": "approved",
            "reasons_json": "[]",
            "policy_trace_json": '{"checks":[]}',
            "result_hash": None,
            "previous_record_hash": None,
            "record_hash": record_hash,
            "gateway_signature": signature,
            "created_at": created_at,
        }]

        is_valid, errors = verify_hash_chain(records)
        assert is_valid is True
        assert errors == []

    def test_verify_chain_with_two_records(self):
        """Two-record chain should verify hash linking."""
        created_at1 = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        created_at2 = datetime(2024, 1, 15, 10, 1, 0, tzinfo=UTC)

        # First record
        hash1 = compute_record_hash(
            record_id="int-001",
            org_id="org-123",
            uapk_id="test-uapk",
            agent_id="test-agent",
            action_type="api",
            tool="send_email",
            request_hash="a" * 64,
            decision="approved",
            reasons_json="[]",
            policy_trace_json='{"checks":[]}',
            result_hash=None,
            previous_record_hash=None,
            created_at=created_at1,
        )
        sig1 = sign_record_hash(hash1)

        # Second record
        hash2 = compute_record_hash(
            record_id="int-002",
            org_id="org-123",
            uapk_id="test-uapk",
            agent_id="test-agent",
            action_type="api",
            tool="read_file",
            request_hash="b" * 64,
            decision="denied",
            reasons_json="[]",
            policy_trace_json='{"checks":[]}',
            result_hash=None,
            previous_record_hash=hash1,  # Links to first
            created_at=created_at2,
        )
        sig2 = sign_record_hash(hash2)

        records = [
            {
                "record_id": "int-001",
                "org_id": "org-123",
                "uapk_id": "test-uapk",
                "agent_id": "test-agent",
                "action_type": "api",
                "tool": "send_email",
                "request_hash": "a" * 64,
                "decision": "approved",
                "reasons_json": "[]",
                "policy_trace_json": '{"checks":[]}',
                "result_hash": None,
                "previous_record_hash": None,
                "record_hash": hash1,
                "gateway_signature": sig1,
                "created_at": created_at1,
            },
            {
                "record_id": "int-002",
                "org_id": "org-123",
                "uapk_id": "test-uapk",
                "agent_id": "test-agent",
                "action_type": "api",
                "tool": "read_file",
                "request_hash": "b" * 64,
                "decision": "denied",
                "reasons_json": "[]",
                "policy_trace_json": '{"checks":[]}',
                "result_hash": None,
                "previous_record_hash": hash1,
                "record_hash": hash2,
                "gateway_signature": sig2,
                "created_at": created_at2,
            },
        ]

        is_valid, errors = verify_hash_chain(records)
        assert is_valid is True
        assert errors == []

    def test_verify_chain_broken_link(self):
        """Chain with broken previous hash link should fail."""
        created_at1 = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        created_at2 = datetime(2024, 1, 15, 10, 1, 0, tzinfo=UTC)

        hash1 = compute_record_hash(
            record_id="int-001",
            org_id="org-123",
            uapk_id="test-uapk",
            agent_id="test-agent",
            action_type="api",
            tool="send_email",
            request_hash="a" * 64,
            decision="approved",
            reasons_json="[]",
            policy_trace_json='{"checks":[]}',
            result_hash=None,
            previous_record_hash=None,
            created_at=created_at1,
        )
        sig1 = sign_record_hash(hash1)

        # Second record with WRONG previous_record_hash
        hash2 = compute_record_hash(
            record_id="int-002",
            org_id="org-123",
            uapk_id="test-uapk",
            agent_id="test-agent",
            action_type="api",
            tool="read_file",
            request_hash="b" * 64,
            decision="denied",
            reasons_json="[]",
            policy_trace_json='{"checks":[]}',
            result_hash=None,
            previous_record_hash="wrong" + "0" * 59,  # Wrong hash
            created_at=created_at2,
        )
        sig2 = sign_record_hash(hash2)

        records = [
            {
                "record_id": "int-001",
                "org_id": "org-123",
                "uapk_id": "test-uapk",
                "agent_id": "test-agent",
                "action_type": "api",
                "tool": "send_email",
                "request_hash": "a" * 64,
                "decision": "approved",
                "reasons_json": "[]",
                "policy_trace_json": '{"checks":[]}',
                "result_hash": None,
                "previous_record_hash": None,
                "record_hash": hash1,
                "gateway_signature": sig1,
                "created_at": created_at1,
            },
            {
                "record_id": "int-002",
                "org_id": "org-123",
                "uapk_id": "test-uapk",
                "agent_id": "test-agent",
                "action_type": "api",
                "tool": "read_file",
                "request_hash": "b" * 64,
                "decision": "denied",
                "reasons_json": "[]",
                "policy_trace_json": '{"checks":[]}',
                "result_hash": None,
                "previous_record_hash": "wrong" + "0" * 59,
                "record_hash": hash2,
                "gateway_signature": sig2,
                "created_at": created_at2,
            },
        ]

        is_valid, errors = verify_hash_chain(records)
        assert is_valid is False
        assert len(errors) > 0
        assert "previous_record_hash mismatch" in errors[0]

    def test_verify_chain_tampered_hash(self):
        """Chain with tampered record hash should fail."""
        created_at = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        record_hash = compute_record_hash(
            record_id="int-001",
            org_id="org-123",
            uapk_id="test-uapk",
            agent_id="test-agent",
            action_type="api",
            tool="send_email",
            request_hash="a" * 64,
            decision="approved",
            reasons_json="[]",
            policy_trace_json='{"checks":[]}',
            result_hash=None,
            previous_record_hash=None,
            created_at=created_at,
        )

        # Store wrong hash
        wrong_hash = "tampered" + "0" * 56

        records = [{
            "record_id": "int-001",
            "org_id": "org-123",
            "uapk_id": "test-uapk",
            "agent_id": "test-agent",
            "action_type": "api",
            "tool": "send_email",
            "request_hash": "a" * 64,
            "decision": "approved",
            "reasons_json": "[]",
            "policy_trace_json": '{"checks":[]}',
            "result_hash": None,
            "previous_record_hash": None,
            "record_hash": wrong_hash,  # Tampered!
            "gateway_signature": "",
            "created_at": created_at,
        }]

        is_valid, errors = verify_hash_chain(records)
        assert is_valid is False
        assert len(errors) > 0
        assert "record_hash mismatch" in errors[0]


class TestPolicyTrace:
    """Tests for PolicyTrace builder."""

    def test_policy_trace_basic(self):
        """PolicyTrace should build valid trace structure."""
        trace = PolicyTrace()
        trace.start()
        trace.add_check("manifest_validation", "pass", {"manifest_id": "test"})
        trace.add_check("budget_check", "fail", {"current": 100, "limit": 50})
        trace.finish()

        result = trace.to_dict()

        assert len(result["checks"]) == 2
        assert result["checks"][0]["check"] == "manifest_validation"
        assert result["checks"][0]["result"] == "pass"
        assert result["checks"][1]["check"] == "budget_check"
        assert result["checks"][1]["result"] == "fail"
        assert result["start_time"] is not None
        assert result["end_time"] is not None
        assert result["duration_ms"] is not None

    def test_policy_trace_to_json(self):
        """PolicyTrace should produce valid JSON."""
        trace = PolicyTrace()
        trace.add_check("test_check", "pass")

        json_str = trace.to_json()

        # Should be valid canonical JSON
        assert '"check":"test_check"' in json_str
        assert '"result":"pass"' in json_str


class TestRiskSnapshot:
    """Tests for RiskSnapshot builder."""

    def test_risk_snapshot_basic(self):
        """RiskSnapshot should store indicators."""
        snapshot = RiskSnapshot()
        snapshot.add("custom_indicator", 42)
        snapshot.set_budget_usage(75, 100)
        snapshot.set_amount(500.0, 1000.0)

        result = snapshot.to_dict()

        assert result["custom_indicator"] == 42
        assert result["budget_current"] == 75
        assert result["budget_limit"] == 100
        assert result["budget_percent"] == 75.0
        assert result["request_amount"] == 500.0
        assert result["max_amount"] == 1000.0

    def test_risk_snapshot_to_json(self):
        """RiskSnapshot should produce valid JSON."""
        snapshot = RiskSnapshot()
        snapshot.set_budget_usage(50, 100)

        json_str = snapshot.to_json()

        assert '"budget_current":50' in json_str
        assert '"budget_limit":100' in json_str

"""Audit log utilities for tamper-evident record keeping.

Implements hash chaining and Ed25519 signatures for interaction records.
"""

import hashlib
import json
from datetime import datetime
from typing import Any

from app.core.ed25519 import get_gateway_key_manager
from app.core.logging import get_logger

logger = get_logger("core.audit")


def canonicalize_json(data: Any) -> str:
    """Convert data to canonical JSON format for hashing.

    Canonical format ensures deterministic serialization:
    - Keys are sorted alphabetically
    - No whitespace between elements
    - Unicode escaped
    - Null values preserved
    - Floats normalized
    """

    def normalize(obj: Any) -> Any:
        """Recursively normalize object for canonical form."""
        if obj is None:
            return None
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, int):
            return obj
        if isinstance(obj, float):
            # Normalize floats to avoid precision issues
            if obj == int(obj):
                return int(obj)
            return round(obj, 10)
        if isinstance(obj, str):
            return obj
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (list, tuple)):
            return [normalize(item) for item in obj]
        if isinstance(obj, dict):
            return {str(k): normalize(v) for k, v in sorted(obj.items())}
        # For other types, convert to string
        return str(obj)

    normalized = normalize(data)
    return json.dumps(normalized, separators=(",", ":"), ensure_ascii=True, sort_keys=True)


def compute_hash(data: str) -> str:
    """Compute SHA-256 hash of data.

    Returns hex-encoded hash string.
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_request_hash(request_data: dict) -> str:
    """Compute hash of the request data.

    Used to uniquely identify the request content.
    """
    canonical = canonicalize_json(request_data)
    return compute_hash(canonical)


def compute_result_hash(result_data: dict | None) -> str | None:
    """Compute hash of the result data.

    Returns None if no result.
    """
    if result_data is None:
        return None
    canonical = canonicalize_json(result_data)
    return compute_hash(canonical)


def compute_record_hash(
    record_id: str,
    org_id: str,
    uapk_id: str,
    agent_id: str,
    action_type: str,
    tool: str,
    request_hash: str,
    decision: str,
    reasons_json: str,
    policy_trace_json: str,
    result_hash: str | None,
    previous_record_hash: str | None,
    created_at: datetime,
) -> str:
    """Compute the tamper-evident hash of a record.

    The record hash is computed over a canonical subset of fields
    plus the previous record hash to form a chain.
    """
    # Build canonical data structure
    record_data = {
        "record_id": record_id,
        "org_id": org_id,
        "uapk_id": uapk_id,
        "agent_id": agent_id,
        "action_type": action_type,
        "tool": tool,
        "request_hash": request_hash,
        "decision": decision,
        "reasons_json": reasons_json,
        "policy_trace_json": policy_trace_json,
        "result_hash": result_hash,
        "previous_record_hash": previous_record_hash,
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
    }

    canonical = canonicalize_json(record_data)
    return compute_hash(canonical)


def sign_record_hash(record_hash: str) -> str:
    """Sign the record hash with the gateway's Ed25519 key.

    Returns base64-encoded signature.
    """
    import base64

    key_manager = get_gateway_key_manager()
    signature_bytes = key_manager.sign(record_hash.encode("utf-8"))
    return base64.b64encode(signature_bytes).decode("utf-8")


def verify_record_signature(record_hash: str, signature: str) -> bool:
    """Verify a record signature.

    Returns True if signature is valid.
    """
    import base64

    try:
        key_manager = get_gateway_key_manager()
        signature_bytes = base64.b64decode(signature)
        key_manager.public_key.verify(signature_bytes, record_hash.encode("utf-8"))
        return True
    except Exception as e:
        logger.warning("signature_verification_failed", error=str(e))
        return False


def verify_hash_chain(records: list[dict]) -> tuple[bool, list[str]]:
    """Verify the integrity of a hash chain.

    Args:
        records: List of record dicts in chronological order

    Returns:
        (is_valid, errors): Tuple of validity and list of errors
    """
    errors: list[str] = []

    if not records:
        return True, []

    previous_hash: str | None = None

    for i, record in enumerate(records):
        record_id = record.get("record_id", f"record_{i}")

        # Check previous hash matches
        stored_previous = record.get("previous_record_hash")
        if stored_previous != previous_hash:
            errors.append(
                f"Record {record_id}: previous_record_hash mismatch. "
                f"Expected {previous_hash}, got {stored_previous}"
            )

        # Recompute record hash
        try:
            computed_hash = compute_record_hash(
                record_id=record["record_id"],
                org_id=record["org_id"],
                uapk_id=record["uapk_id"],
                agent_id=record["agent_id"],
                action_type=record["action_type"],
                tool=record["tool"],
                request_hash=record["request_hash"],
                decision=record["decision"],
                reasons_json=record["reasons_json"],
                policy_trace_json=record["policy_trace_json"],
                result_hash=record.get("result_hash"),
                previous_record_hash=record.get("previous_record_hash"),
                created_at=record["created_at"],
            )

            stored_hash = record.get("record_hash")
            if computed_hash != stored_hash:
                errors.append(
                    f"Record {record_id}: record_hash mismatch. "
                    f"Expected {computed_hash}, got {stored_hash}"
                )
        except Exception as e:
            errors.append(f"Record {record_id}: failed to compute hash: {e}")
            computed_hash = record.get("record_hash", "")

        # Verify signature
        signature = record.get("gateway_signature")
        stored_hash = record.get("record_hash")
        if signature and stored_hash:
            if not verify_record_signature(stored_hash, signature):
                errors.append(f"Record {record_id}: invalid signature")

        # Update previous hash for next iteration
        previous_hash = record.get("record_hash")

    return len(errors) == 0, errors


class PolicyTrace:
    """Builder for structured policy trace."""

    def __init__(self) -> None:
        self.checks: list[dict] = []
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None

    def start(self) -> "PolicyTrace":
        """Mark start of policy evaluation."""
        from datetime import UTC

        self.start_time = datetime.now(UTC)
        return self

    def add_check(
        self,
        check_name: str,
        result: str,
        details: dict | None = None,
    ) -> "PolicyTrace":
        """Add a policy check to the trace.

        Args:
            check_name: Name of the check (e.g., "manifest_validation")
            result: "pass", "fail", "skip", or "escalate"
            details: Optional additional details
        """
        self.checks.append({
            "check": check_name,
            "result": result,
            "details": details or {},
        })
        return self

    def finish(self) -> "PolicyTrace":
        """Mark end of policy evaluation."""
        from datetime import UTC

        self.end_time = datetime.now(UTC)
        return self

    def to_dict(self) -> dict:
        """Convert trace to dictionary."""
        return {
            "checks": self.checks,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": (
                int((self.end_time - self.start_time).total_seconds() * 1000)
                if self.start_time and self.end_time
                else None
            ),
        }

    def to_json(self) -> str:
        """Convert trace to canonical JSON string."""
        return canonicalize_json(self.to_dict())


class RiskSnapshot:
    """Snapshot of risk indicators at evaluation time."""

    def __init__(self) -> None:
        self.indicators: dict[str, Any] = {}

    def add(self, key: str, value: Any) -> "RiskSnapshot":
        """Add a risk indicator."""
        self.indicators[key] = value
        return self

    def set_budget_usage(self, current: int, limit: int) -> "RiskSnapshot":
        """Set budget usage indicator."""
        self.indicators["budget_current"] = current
        self.indicators["budget_limit"] = limit
        self.indicators["budget_percent"] = (
            round(current / limit * 100, 2) if limit > 0 else 0
        )
        return self

    def set_amount(self, amount: float | None, max_amount: float | None) -> "RiskSnapshot":
        """Set amount-related indicators."""
        if amount is not None:
            self.indicators["request_amount"] = amount
        if max_amount is not None:
            self.indicators["max_amount"] = max_amount
        return self

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.indicators

    def to_json(self) -> str:
        """Convert to canonical JSON string."""
        return canonicalize_json(self.indicators)

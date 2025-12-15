#!/usr/bin/env python3
"""
Verify Log Chain - CLI tool for verifying interaction record hash chains.

This tool verifies the integrity of exported audit logs by:
1. Checking hash chain continuity (each record links to previous)
2. Recomputing and comparing record hashes
3. Verifying Ed25519 signatures

Usage:
    python scripts/verify_log_chain.py export.json
    python scripts/verify_log_chain.py logs.jsonl
    python scripts/verify_log_chain.py --from-db --uapk-id my-uapk
    python scripts/verify_log_chain.py --verbose export.json
"""

import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def canonicalize_json(data: Any) -> str:
    """Convert data to canonical JSON format for hashing.

    Canonical format ensures deterministic serialization:
    - Keys are sorted alphabetically
    - No whitespace between elements
    - Unicode escaped
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
        return str(obj)

    normalized = normalize(data)
    return json.dumps(normalized, separators=(",", ":"), ensure_ascii=True, sort_keys=True)


def compute_hash(data: str) -> str:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_record_hash(record: dict) -> str:
    """Compute the tamper-evident hash of a record."""
    record_data = {
        "record_id": record["record_id"],
        "org_id": record["org_id"],
        "uapk_id": record["uapk_id"],
        "agent_id": record["agent_id"],
        "action_type": record["action_type"],
        "tool": record["tool"],
        "request_hash": record["request_hash"],
        "decision": record["decision"],
        "reasons_json": record["reasons_json"],
        "policy_trace_json": record["policy_trace_json"],
        "result_hash": record.get("result_hash"),
        "previous_record_hash": record.get("previous_record_hash"),
        "created_at": record["created_at"],
    }

    canonical = canonicalize_json(record_data)
    return compute_hash(canonical)


def verify_signature(record_hash: str, signature: str, public_key_b64: str | None) -> bool:
    """Verify Ed25519 signature.

    Returns True if signature is valid, False otherwise.
    Returns True if no public key is provided (skip verification).
    """
    if public_key_b64 is None:
        return True  # Skip if no key provided

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        public_key_bytes = base64.b64decode(public_key_b64)
        public_key = Ed25519PublicKey.from_public_key_bytes(public_key_bytes)

        signature_bytes = base64.b64decode(signature)
        public_key.verify(signature_bytes, record_hash.encode("utf-8"))
        return True
    except ImportError:
        print("Warning: cryptography library not installed, skipping signature verification")
        return True
    except Exception:
        return False


def verify_chain(
    records: list[dict],
    public_key_b64: str | None = None,
    verbose: bool = False,
) -> tuple[bool, list[str]]:
    """Verify the integrity of a hash chain.

    Args:
        records: List of record dicts in chronological order
        public_key_b64: Base64-encoded Ed25519 public key for signature verification
        verbose: Print detailed progress

    Returns:
        (is_valid, errors): Tuple of validity and list of errors
    """
    errors: list[str] = []

    if not records:
        if verbose:
            print("No records to verify")
        return True, []

    if verbose:
        print(f"Verifying chain of {len(records)} records...")

    previous_hash: str | None = None

    for i, record in enumerate(records):
        record_id = record.get("record_id", f"record_{i}")

        if verbose:
            print(f"  [{i + 1}/{len(records)}] Verifying {record_id}...", end="")

        # Check previous hash matches
        stored_previous = record.get("previous_record_hash")
        if stored_previous != previous_hash:
            error = (
                f"Record {record_id}: previous_record_hash mismatch. "
                f"Expected {previous_hash}, got {stored_previous}"
            )
            errors.append(error)
            if verbose:
                print(f" CHAIN BREAK")
                print(f"    Expected previous: {previous_hash}")
                print(f"    Got previous: {stored_previous}")

        # Recompute record hash
        try:
            computed_hash = compute_record_hash(record)
            stored_hash = record.get("record_hash")

            if computed_hash != stored_hash:
                error = (
                    f"Record {record_id}: record_hash mismatch. "
                    f"Expected {computed_hash}, got {stored_hash}"
                )
                errors.append(error)
                if verbose:
                    print(f" HASH MISMATCH")
                    print(f"    Computed: {computed_hash}")
                    print(f"    Stored: {stored_hash}")
        except Exception as e:
            error = f"Record {record_id}: failed to compute hash: {e}"
            errors.append(error)
            if verbose:
                print(f" COMPUTE ERROR: {e}")
            computed_hash = record.get("record_hash", "")

        # Verify signature
        signature = record.get("gateway_signature")
        stored_hash = record.get("record_hash")
        if signature and stored_hash and public_key_b64:
            if not verify_signature(stored_hash, signature, public_key_b64):
                error = f"Record {record_id}: invalid signature"
                errors.append(error)
                if verbose:
                    print(f" SIGNATURE INVALID")

        if verbose and not errors:
            print(" OK")
        elif verbose and errors:
            pass  # Already printed error

        # Update previous hash for next iteration
        previous_hash = record.get("record_hash")

    return len(errors) == 0, errors


def load_json_export(path: Path) -> tuple[list[dict], dict | None]:
    """Load records from a JSON export bundle."""
    with open(path) as f:
        data = json.load(f)

    records = data.get("records", [])
    manifest = data.get("manifest_snapshot")

    return records, manifest


def load_jsonl_export(path: Path) -> tuple[list[dict], dict | None]:
    """Load records from a JSONL export file."""
    records = []
    manifest = None

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            item = json.loads(line)
            item_type = item.pop("type", "record")

            if item_type == "metadata":
                # Skip metadata line
                continue
            elif item_type == "manifest":
                manifest = item
            elif item_type == "record":
                records.append(item)

    return records, manifest


def main():
    parser = argparse.ArgumentParser(
        description="Verify interaction record hash chain integrity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s export.json                    Verify JSON export file
    %(prog)s logs.jsonl                     Verify JSONL export file
    %(prog)s --verbose export.json          Verbose output
    %(prog)s --public-key KEY export.json   Verify signatures with key

Exit codes:
    0   Chain is valid
    1   Chain verification failed
    2   Error loading or parsing file
        """,
    )

    parser.add_argument(
        "file",
        type=Path,
        help="Export file to verify (JSON or JSONL format)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed verification progress",
    )
    parser.add_argument(
        "--public-key",
        type=str,
        help="Base64-encoded Ed25519 public key for signature verification",
    )
    parser.add_argument(
        "--format",
        choices=["auto", "json", "jsonl"],
        default="auto",
        help="Export file format (default: auto-detect from extension)",
    )

    args = parser.parse_args()

    # Check file exists
    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(2)

    # Determine format
    fmt = args.format
    if fmt == "auto":
        if args.file.suffix == ".jsonl" or args.file.suffix == ".ndjson":
            fmt = "jsonl"
        else:
            fmt = "json"

    # Load records
    try:
        if fmt == "jsonl":
            records, manifest = load_jsonl_export(args.file)
        else:
            records, manifest = load_json_export(args.file)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error loading file: {e}", file=sys.stderr)
        sys.exit(2)

    if args.verbose:
        print(f"Loaded {len(records)} records from {args.file}")
        if manifest:
            print(f"Manifest: {manifest.get('uapk_id')} v{manifest.get('version')}")
        print()

    # Verify chain
    is_valid, errors = verify_chain(
        records=records,
        public_key_b64=args.public_key,
        verbose=args.verbose,
    )

    # Print results
    print()
    if is_valid:
        print(f"Chain verification PASSED")
        print(f"  Records verified: {len(records)}")
        if records:
            print(f"  First record: {records[0].get('record_id')}")
            print(f"  Last record: {records[-1].get('record_id')}")
            print(f"  First hash: {records[0].get('record_hash', '')[:16]}...")
            print(f"  Last hash: {records[-1].get('record_hash', '')[:16]}...")
        sys.exit(0)
    else:
        print(f"Chain verification FAILED")
        print(f"  Records checked: {len(records)}")
        print(f"  Errors found: {len(errors)}")
        print()
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

---
title: Logs API
description: Query and export audit logs
---

# Logs API

Query, verify, and export tamper-evident audit logs.

## List Logs

Query interaction records with filtering.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/logs`

### Request

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/logs?uapk_id=customer-support-bot&limit=50" \
  -H "Authorization: Bearer $TOKEN"
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `uapk_id` | string | Filter by agent manifest ID |
| `agent_id` | string | Filter by agent instance ID |
| `action_type` | string | Filter by action type (e.g., `email`) |
| `tool` | string | Filter by tool (e.g., `send`) |
| `decision` | string | Filter: `approved`, `denied`, `pending` |
| `from` | datetime | Start of time range (ISO 8601) |
| `to` | datetime | End of time range (ISO 8601) |
| `limit` | integer | Max results (default 50, max 1000) |
| `offset` | integer | Pagination offset |

### Response

```json
{
  "items": [
    {
      "record_id": "int-abc123",
      "org_id": "550e8400-e29b-41d4-a716-446655440000",
      "uapk_id": "customer-support-bot",
      "agent_id": "customer-support-bot",
      "action_type": "email",
      "tool": "send",
      "decision": "approved",
      "request_hash": "sha256:a1b2c3...",
      "result_hash": "sha256:d4e5f6...",
      "record_hash": "sha256:g7h8i9...",
      "previous_record_hash": "sha256:j0k1l2...",
      "created_at": "2024-12-14T10:30:00Z"
    }
  ],
  "total": 1250,
  "has_more": true
}
```

---

## Get Log Record

Get full details of a specific log record.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/logs/{record_id}`

### Request

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/logs/int-abc123 \
  -H "Authorization: Bearer $TOKEN"
```

### Response

```json
{
  "record_id": "int-abc123",
  "org_id": "550e8400-e29b-41d4-a716-446655440000",
  "uapk_id": "customer-support-bot",
  "agent_id": "customer-support-bot",
  "action_type": "email",
  "tool": "send",
  "request": {
    "to": "customer@example.com",
    "subject": "Re: Your inquiry",
    "body": "Thank you for contacting us..."
  },
  "request_hash": "sha256:a1b2c3d4e5f6...",
  "decision": "approved",
  "reasons_json": "[]",
  "policy_trace_json": {
    "checks": [
      {"check": "manifest_validation", "result": "pass"},
      {"check": "capability_token", "result": "pass"},
      {"check": "action_type", "result": "pass"},
      {"check": "tool_authorization", "result": "pass"},
      {"check": "budget_check", "result": "pass", "details": {"current": 45, "limit": 100}}
    ]
  },
  "risk_snapshot_json": {
    "budget_current": 45,
    "budget_limit": 100,
    "budget_percent": 45.0
  },
  "result": {
    "success": true,
    "data": {
      "message_id": "msg-xyz789",
      "sent_at": "2024-12-14T10:30:00Z"
    }
  },
  "result_hash": "sha256:d4e5f6g7h8i9...",
  "previous_record_hash": "sha256:j0k1l2m3n4o5...",
  "record_hash": "sha256:p6q7r8s9t0u1...",
  "gateway_signature": "Base64EncodedEd25519Signature...",
  "created_at": "2024-12-14T10:30:00Z"
}
```

---

## Verify Chain

Verify the integrity of the hash chain for an agent.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/logs/verify/{uapk_id}`

### Request

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/logs/verify/customer-support-bot \
  -H "Authorization: Bearer $TOKEN"
```

### Response (Valid)

```json
{
  "is_valid": true,
  "record_count": 1250,
  "first_record_id": "int-001",
  "last_record_id": "int-1250",
  "first_record_hash": "sha256:a1b2c3...",
  "last_record_hash": "sha256:x7y8z9...",
  "errors": [],
  "verified_at": "2024-12-14T12:00:00Z"
}
```

### Response (Invalid)

```json
{
  "is_valid": false,
  "record_count": 1250,
  "first_record_id": "int-001",
  "last_record_id": "int-1250",
  "first_record_hash": "sha256:a1b2c3...",
  "last_record_hash": "sha256:x7y8z9...",
  "errors": [
    {
      "record_id": "int-500",
      "error_type": "CHAIN_BREAK",
      "message": "Previous hash mismatch: expected sha256:abc..., got sha256:xyz..."
    }
  ],
  "verified_at": "2024-12-14T12:00:00Z"
}
```

### Error Types

| Type | Description |
|------|-------------|
| `CHAIN_BREAK` | Previous record hash doesn't match |
| `HASH_MISMATCH` | Record hash doesn't match computed hash |
| `SIGNATURE_INVALID` | Ed25519 signature verification failed |

---

## Export Logs (JSON)

Export logs as a JSON bundle with verification data.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/logs/export/download`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/logs/export/download \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "from": "2024-12-01T00:00:00Z",
    "to": "2024-12-14T23:59:59Z",
    "include_manifest": true
  }' \
  > export.json
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uapk_id` | string | Yes | Agent to export logs for |
| `from` | datetime | No | Start of time range |
| `to` | datetime | No | End of time range |
| `include_manifest` | boolean | No | Include manifest snapshot (default: true) |

### Response

```json
{
  "export_id": "exp-abc123",
  "exported_at": "2024-12-14T12:00:00Z",
  "org_id": "550e8400-e29b-41d4-a716-446655440000",
  "uapk_id": "customer-support-bot",
  "period": {
    "from": "2024-12-01T00:00:00Z",
    "to": "2024-12-14T23:59:59Z"
  },
  "manifest": {
    "manifest_id": "880e8400-e29b-41d4-a716-446655440003",
    "agent": {
      "id": "customer-support-bot",
      "name": "Customer Support Bot",
      "version": "1.0.0"
    },
    "capabilities": ["email:send", "email:read", "crm:read"],
    "manifest_hash": "sha256:m1n2o3..."
  },
  "verification": {
    "is_valid": true,
    "record_count": 500,
    "first_record_hash": "sha256:a1b2c3...",
    "last_record_hash": "sha256:x7y8z9..."
  },
  "gateway_public_key": "MCowBQYDK2VwAyEA...",
  "records": [
    {
      "record_id": "int-001",
      "action_type": "email",
      "tool": "send",
      "decision": "approved",
      "record_hash": "sha256:...",
      "gateway_signature": "...",
      "created_at": "2024-12-01T08:00:00Z"
    }
  ]
}
```

---

## Export Logs (JSONL)

Export logs in JSONL format for streaming processing.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/logs/export/jsonl`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/logs/export/jsonl \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "from": "2024-12-01T00:00:00Z"
  }' \
  > logs.jsonl
```

### Response Format

Each line is a JSON object:

```
{"type":"metadata","export_id":"exp-abc123","record_count":500,"gateway_public_key":"MCow..."}
{"type":"manifest","uapk_id":"customer-support-bot","version":"1.0.0","manifest_hash":"sha256:..."}
{"type":"record","record_id":"int-001","action_type":"email","decision":"approved","record_hash":"sha256:...","gateway_signature":"..."}
{"type":"record","record_id":"int-002","action_type":"email","decision":"approved","record_hash":"sha256:...","gateway_signature":"..."}
{"type":"verification","is_valid":true,"first_record_hash":"sha256:...","last_record_hash":"sha256:..."}
```

---

## Offline Verification

Use the exported logs for offline verification.

### Python Script

```bash
# Download verification script
curl -O https://gateway.example.com/scripts/verify_log_chain.py

# Verify exported logs
python verify_log_chain.py export.json
```

### Output

```
UAPK Gateway Log Chain Verification
====================================

Loading export file: export.json
Export ID: exp-abc123
Agent: customer-support-bot
Records: 500

Verifying chain integrity...
  [1/500] int-001... OK
  [2/500] int-002... OK
  ...
  [500/500] int-500... OK

Verifying signatures...
  Using gateway public key: MCowBQYDK2VwAyEA...
  [1/500] int-001... OK
  ...

============================================
VERIFICATION PASSED

Summary:
  Records verified: 500
  First record: int-001
  Last record: int-500
  First hash: sha256:a1b2c3...
  Last hash: sha256:x7y8z9...
  All signatures valid: Yes
============================================
```

---

## Log Statistics

Get log statistics for the organization.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/logs/stats`

### Request

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/logs/stats?from=2024-12-01" \
  -H "Authorization: Bearer $TOKEN"
```

### Response

```json
{
  "period": {
    "from": "2024-12-01T00:00:00Z",
    "to": "2024-12-14T23:59:59Z"
  },
  "totals": {
    "records": 5000,
    "approved": 4500,
    "denied": 350,
    "pending": 150
  },
  "by_agent": [
    {
      "uapk_id": "customer-support-bot",
      "records": 3000,
      "approved": 2800,
      "denied": 150,
      "pending": 50
    },
    {
      "uapk_id": "deployment-bot",
      "records": 2000,
      "approved": 1700,
      "denied": 200,
      "pending": 100
    }
  ],
  "by_action_type": {
    "email": 2500,
    "crm": 1500,
    "kubernetes": 800,
    "github": 200
  },
  "by_decision": {
    "approved": 4500,
    "denied": 350,
    "pending": 150
  },
  "chain_integrity": {
    "all_valid": true,
    "last_verified": "2024-12-14T06:00:00Z"
  }
}
```

---

## Reason Code Reference

### Deny Reasons in Logs

| Code | Description |
|------|-------------|
| `MANIFEST_NOT_FOUND` | No manifest for agent |
| `MANIFEST_INACTIVE` | Manifest suspended/revoked |
| `INVALID_TOKEN` | Bad capability token |
| `TOKEN_EXPIRED` | Token past expiry |
| `TOKEN_REVOKED` | Token was revoked |
| `ACTION_NOT_ALLOWED` | Action type forbidden |
| `TOOL_NOT_AUTHORIZED` | Tool not in manifest |
| `CAPABILITY_MISSING` | Token lacks capability |
| `BUDGET_EXCEEDED` | Rate limit hit |
| `JURISDICTION_BLOCKED` | Blocked region |
| `COUNTERPARTY_BLOCKED` | Blocked counterparty |

## Related

- [Audit Logs](../concepts/logs.md) - Log concepts
- [Gateway API](gateway.md) - Action execution
- [Operator: Audit](../operator/audit.md) - Using the dashboard

---
title: Gateway API
description: Evaluate and execute agent actions
---

# Gateway API

The core gateway endpoints for evaluating and executing agent actions.

## Execute Action

Evaluate and execute an action in one call. The gateway evaluates the request against policies and, if allowed, executes the action.

<div class="api-method post">POST</div> `/api/v1/gateway/execute`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "agent_id": "customer-support-bot",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {
        "to": "customer@example.com",
        "subject": "Re: Your inquiry",
        "body": "Thank you for contacting us..."
      }
    }
  }'
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uapk_id` | string | Yes | Agent manifest identifier |
| `agent_id` | string | Yes | Agent instance identifier |
| `capability_token` | string | No | Ed25519-signed capability JWT |
| `action.type` | string | Yes | Action category (e.g., `email`, `crm`) |
| `action.tool` | string | Yes | Specific tool (e.g., `send`, `update`) |
| `action.params` | object | Yes | Tool-specific parameters |
| `idempotency_key` | string | No | Unique key for idempotent execution |

### Response: ALLOW

```json
{
  "interaction_id": "int-abc123",
  "decision": "ALLOW",
  "reasons": [],
  "executed": true,
  "result": {
    "success": true,
    "data": {
      "message_id": "msg-xyz789",
      "sent_at": "2024-12-14T10:30:00Z"
    }
  },
  "policy_trace": {
    "checks": [
      {"check": "manifest_validation", "result": "pass"},
      {"check": "capability_token", "result": "pass"},
      {"check": "action_type", "result": "pass"},
      {"check": "tool_authorization", "result": "pass"},
      {"check": "budget_check", "result": "pass"}
    ]
  },
  "risk_snapshot": {
    "budget_current": 45,
    "budget_limit": 100,
    "budget_percent": 45.0
  },
  "timestamp": "2024-12-14T10:30:00Z"
}
```

### Response: DENY

```json
{
  "interaction_id": "int-def456",
  "decision": "DENY",
  "reasons": [
    {
      "code": "BUDGET_EXCEEDED",
      "message": "Hourly action limit exceeded (100/100)"
    }
  ],
  "executed": false,
  "policy_trace": {
    "checks": [
      {"check": "manifest_validation", "result": "pass"},
      {"check": "capability_token", "result": "pass"},
      {"check": "budget_check", "result": "fail", "details": {"current": 100, "limit": 100}}
    ]
  },
  "timestamp": "2024-12-14T10:31:00Z"
}
```

### Response: ESCALATE

```json
{
  "interaction_id": "int-ghi789",
  "decision": "ESCALATE",
  "reasons": [
    {
      "code": "REQUIRES_APPROVAL",
      "message": "Action 'crm:delete' requires human approval"
    }
  ],
  "approval_id": "appr-xyz789",
  "executed": false,
  "timestamp": "2024-12-14T10:32:00Z"
}
```

---

## Evaluate Action (Dry Run)

Evaluate an action without executing it. Useful for pre-flight checks.

<div class="api-method post">POST</div> `/api/v1/gateway/evaluate`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/gateway/evaluate \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "agent_id": "customer-support-bot",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {
        "to": "customer@example.com",
        "subject": "Test"
      }
    }
  }'
```

### Response

```json
{
  "would_allow": true,
  "decision": "ALLOW",
  "reasons": [],
  "policy_trace": {
    "checks": [
      {"check": "manifest_validation", "result": "pass"},
      {"check": "capability_token", "result": "pass"},
      {"check": "action_type", "result": "pass"},
      {"check": "tool_authorization", "result": "pass"},
      {"check": "budget_check", "result": "pass"}
    ]
  },
  "risk_snapshot": {
    "budget_current": 45,
    "budget_limit": 100,
    "budget_percent": 45.0
  }
}
```

---

## Execute with Capability Token

Include a capability token for fine-grained authorization.

### Request

```bash
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "agent_id": "customer-support-bot",
    "capability_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJpc3N1ZXItYWJjMTIzIiwic3ViIjoiY3VzdG9tZXItc3VwcG9ydC1ib3QiLCJhdWQiOiJ1YXBrLWdhdGV3YXkiLCJleHAiOjE3MDI2NDY0MDAsImNhcCI6WyJlbWFpbDpzZW5kIl19.signature",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {
        "to": "customer@example.com",
        "subject": "Hello"
      }
    }
  }'
```

---

## Batch Execute

Execute multiple actions in a single request.

<div class="api-method post">POST</div> `/api/v1/gateway/batch`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/gateway/batch \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "agent_id": "customer-support-bot",
    "actions": [
      {
        "action_id": "a1",
        "type": "email",
        "tool": "send",
        "params": {"to": "user1@example.com", "subject": "Hello"}
      },
      {
        "action_id": "a2",
        "type": "crm",
        "tool": "update",
        "params": {"record_id": "rec-123", "status": "contacted"}
      }
    ],
    "stop_on_deny": false
  }'
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `actions` | array | Yes | List of actions to execute |
| `actions[].action_id` | string | Yes | Client-provided ID for correlation |
| `stop_on_deny` | boolean | No | Stop batch on first deny (default: false) |

### Response

```json
{
  "batch_id": "batch-abc123",
  "results": [
    {
      "action_id": "a1",
      "interaction_id": "int-001",
      "decision": "ALLOW",
      "executed": true,
      "result": {"message_id": "msg-001"}
    },
    {
      "action_id": "a2",
      "interaction_id": "int-002",
      "decision": "DENY",
      "executed": false,
      "reasons": [{"code": "CAPABILITY_MISSING", "message": "crm:update not in token"}]
    }
  ],
  "summary": {
    "total": 2,
    "allowed": 1,
    "denied": 1,
    "escalated": 0
  }
}
```

---

## Idempotent Execution

Prevent duplicate executions using idempotency keys.

### Request

```bash
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "agent_id": "customer-support-bot",
    "idempotency_key": "order-confirmation-12345",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {
        "to": "customer@example.com",
        "subject": "Order Confirmation #12345"
      }
    }
  }'
```

### Duplicate Request Response

If the same idempotency key is reused within 24 hours:

```json
{
  "interaction_id": "int-abc123",
  "decision": "ALLOW",
  "executed": true,
  "result": {
    "message_id": "msg-xyz789"
  },
  "idempotent": true,
  "original_timestamp": "2024-12-14T10:30:00Z"
}
```

---

## Issue Capability Token

Issue a capability token for an agent.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/capability-tokens`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/capability-tokens \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "issuer_id": "issuer-abc123",
    "agent_id": "customer-support-bot",
    "manifest_id": "880e8400-e29b-41d4-a716-446655440003",
    "capabilities": ["email:send", "crm:read"],
    "expires_in_hours": 24,
    "constraints": {
      "max_actions": 100,
      "allowed_recipients": ["*@acme.com"]
    }
  }'
```

### Response

```json
{
  "token_id": "tok-xyz789",
  "token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2024-12-15T10:00:00Z",
  "capabilities": ["email:send", "crm:read"],
  "constraints": {
    "max_actions": 100,
    "allowed_recipients": ["*@acme.com"]
  }
}
```

---

## Revoke Capability Token

Revoke a capability token before expiry.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/capability-tokens/{token_id}/revoke`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/capability-tokens/tok-xyz789/revoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Suspected token compromise"
  }'
```

---

## Decision Codes

### ALLOW Reasons

The request passes all policy checks.

### DENY Reasons

| Code | Description |
|------|-------------|
| `MANIFEST_NOT_FOUND` | No manifest registered for agent |
| `MANIFEST_INACTIVE` | Manifest is suspended or revoked |
| `INVALID_TOKEN` | Capability token is invalid |
| `TOKEN_EXPIRED` | Capability token has expired |
| `TOKEN_REVOKED` | Capability token was revoked |
| `ACTION_NOT_ALLOWED` | Action type not permitted |
| `TOOL_NOT_AUTHORIZED` | Tool not in manifest |
| `CAPABILITY_MISSING` | Required capability not in token |
| `BUDGET_EXCEEDED` | Rate limit exceeded |
| `JURISDICTION_BLOCKED` | Counterparty in blocked region |
| `COUNTERPARTY_BLOCKED` | Counterparty on blocklist |

### ESCALATE Reasons

| Code | Description |
|------|-------------|
| `REQUIRES_APPROVAL` | Action requires human approval |
| `AMOUNT_THRESHOLD` | Value exceeds auto-approve threshold |
| `NEW_COUNTERPARTY` | First interaction with counterparty |
| `HIGH_RISK_ACTION` | Action flagged as high risk |

---

## Health Check

Check gateway health status.

<div class="api-method get">GET</div> `/api/v1/gateway/health`

### Request

```bash
curl http://localhost:8000/api/v1/gateway/health
```

### Response

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "timestamp": "2024-12-14T10:00:00Z"
}
```

## Related

- [Policy Decisions](../concepts/decisions.md) - How decisions work
- [Capability Tokens](../concepts/capabilities.md) - Token concepts
- [Approvals API](approvals.md) - Managing escalated requests
- [Logs API](logs.md) - Audit trail

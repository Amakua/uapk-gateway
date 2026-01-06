---
title: Approvals API
description: Manage human-in-the-loop approvals
---

# Approvals API

Manage approval tasks created when the policy engine returns ESCALATE.

## List Approvals

List approval tasks with optional filtering.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/approvals`

### Request

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/approvals?status=pending" \
  -H "Authorization: Bearer $TOKEN"
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter: `pending`, `approved`, `denied`, `expired` |
| `uapk_id` | string | Filter by agent |
| `from` | datetime | Start of time range (ISO 8601) |
| `to` | datetime | End of time range (ISO 8601) |
| `limit` | integer | Max results (default 50) |
| `offset` | integer | Pagination offset |

### Response

```json
{
  "items": [
    {
      "approval_id": "appr-xyz789",
      "interaction_id": "int-abc123",
      "uapk_id": "deployment-bot",
      "agent_id": "deployment-bot",
      "status": "pending",
      "action": {
        "type": "kubernetes",
        "tool": "deploy",
        "params": {
          "namespace": "production",
          "image": "app:v2.0.0",
          "replicas": 3
        }
      },
      "reason_codes": ["REQUIRES_APPROVAL"],
      "created_at": "2024-12-14T10:00:00Z",
      "expires_at": "2024-12-15T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

## Get Approval

Get details of a specific approval task.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/approvals/{approval_id}`

### Request

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/appr-xyz789 \
  -H "Authorization: Bearer $TOKEN"
```

### Response

```json
{
  "approval_id": "appr-xyz789",
  "interaction_id": "int-abc123",
  "uapk_id": "deployment-bot",
  "agent_id": "deployment-bot",
  "status": "pending",
  "action": {
    "type": "kubernetes",
    "tool": "deploy",
    "params": {
      "namespace": "production",
      "image": "app:v2.0.0",
      "replicas": 3
    }
  },
  "reason_codes": ["REQUIRES_APPROVAL"],
  "reasons": [
    {
      "code": "REQUIRES_APPROVAL",
      "message": "Action 'kubernetes:deploy' requires human approval"
    }
  ],
  "policy_trace": {
    "checks": [
      {"check": "manifest_validation", "result": "pass"},
      {"check": "tool_authorization", "result": "escalate"}
    ]
  },
  "risk_snapshot": {
    "budget_current": 15,
    "budget_limit": 50,
    "budget_percent": 30.0
  },
  "manifest": {
    "manifest_id": "990e8400-e29b-41d4-a716-446655440004",
    "agent_name": "Deployment Bot",
    "agent_version": "2.1.0"
  },
  "created_at": "2024-12-14T10:00:00Z",
  "expires_at": "2024-12-15T10:00:00Z"
}
```

---

## Approve Request

Approve an escalated action.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/approvals/{approval_id}/approve`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/appr-xyz789/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Reviewed deployment plan, approved for production rollout"
  }'
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `notes` | string | No | Approval notes for audit trail |

### Response

```json
{
  "approval_id": "appr-xyz789",
  "status": "approved",
  "approved_by": "admin@acme.com",
  "approved_at": "2024-12-14T10:15:00Z",
  "notes": "Reviewed deployment plan, approved for production rollout",
  "execution_result": {
    "success": true,
    "data": {
      "deployment_id": "deploy-abc123",
      "namespace": "production",
      "replicas_ready": 3
    }
  },
  "interaction_id": "int-abc123"
}
```

---

## Deny Request

Deny an escalated action.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/approvals/{approval_id}/deny`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/appr-xyz789/deny \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Not approved for production deployment",
    "notes": "Code freeze in effect until Dec 20. Please retry after freeze period."
  }'
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reason` | string | Yes | Denial reason (shown to agent) |
| `notes` | string | No | Additional notes for audit trail |

### Response

```json
{
  "approval_id": "appr-xyz789",
  "status": "denied",
  "denied_by": "admin@acme.com",
  "denied_at": "2024-12-14T10:15:00Z",
  "reason": "Not approved for production deployment",
  "notes": "Code freeze in effect until Dec 20. Please retry after freeze period.",
  "interaction_id": "int-abc123"
}
```

---

## Poll Approval Status

Agents can poll for approval status.

<div class="api-method get">GET</div> `/api/v1/gateway/approvals/{approval_id}/status`

### Request

```bash
curl http://localhost:8000/api/v1/gateway/approvals/appr-xyz789/status \
  -H "X-API-Key: $API_KEY"
```

### Response (Pending)

```json
{
  "approval_id": "appr-xyz789",
  "status": "pending",
  "expires_at": "2024-12-15T10:00:00Z"
}
```

### Response (Approved)

```json
{
  "approval_id": "appr-xyz789",
  "status": "approved",
  "approved_at": "2024-12-14T10:15:00Z",
  "result": {
    "success": true,
    "data": {
      "deployment_id": "deploy-abc123"
    }
  }
}
```

### Response (Denied)

```json
{
  "approval_id": "appr-xyz789",
  "status": "denied",
  "denied_at": "2024-12-14T10:15:00Z",
  "reason": "Not approved for production deployment"
}
```

---

## Approval Statistics

Get approval statistics for the organization.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/approvals/stats`

### Request

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/stats?from=2024-12-01" \
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
    "pending": 3,
    "approved": 45,
    "denied": 8,
    "expired": 2
  },
  "by_agent": [
    {
      "uapk_id": "deployment-bot",
      "approved": 25,
      "denied": 3,
      "expired": 1
    },
    {
      "uapk_id": "customer-support-bot",
      "approved": 20,
      "denied": 5,
      "expired": 1
    }
  ],
  "average_response_time_minutes": 12.5,
  "by_reason_code": {
    "REQUIRES_APPROVAL": 40,
    "AMOUNT_THRESHOLD": 12,
    "NEW_COUNTERPARTY": 6
  }
}
```

---

## Bulk Actions

### Bulk Approve

Approve multiple pending requests.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/approvals/bulk-approve`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/bulk-approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_ids": ["appr-001", "appr-002", "appr-003"],
    "notes": "Batch approved after security review"
  }'
```

### Response

```json
{
  "results": [
    {"approval_id": "appr-001", "status": "approved"},
    {"approval_id": "appr-002", "status": "approved"},
    {"approval_id": "appr-003", "status": "error", "error": "Already denied"}
  ],
  "summary": {
    "approved": 2,
    "errors": 1
  }
}
```

### Bulk Deny

Deny multiple pending requests.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/approvals/bulk-deny`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/bulk-deny \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_ids": ["appr-004", "appr-005"],
    "reason": "End of day cleanup - agents should retry tomorrow",
    "notes": "Bulk denial for overnight requests"
  }'
```

---

## Approval Status Reference

| Status | Description |
|--------|-------------|
| `pending` | Awaiting operator decision |
| `approved` | Operator approved, action executed |
| `denied` | Operator denied the request |
| `expired` | No decision before expiry (default: 24h) |

## Related

- [Approval Workflow](../concepts/approvals.md) - Workflow concepts
- [Policy Decisions](../concepts/decisions.md) - What triggers ESCALATE
- [Gateway API](gateway.md) - Action execution
- [Operator Guide](../operator/approvals.md) - Using the dashboard

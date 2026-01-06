---
title: Manifests API
description: Register and manage agent manifests
---

# Manifests API

Register, approve, and manage UAPK agent manifests.

## Register Manifest

Register a new agent manifest for approval.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/manifests`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/manifests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.0",
    "agent": {
      "id": "customer-support-bot",
      "name": "Customer Support Bot",
      "version": "1.0.0",
      "description": "AI agent for handling customer inquiries",
      "organization": "acme-corp",
      "team": "support"
    },
    "capabilities": {
      "requested": [
        "email:send",
        "email:read",
        "crm:read",
        "crm:update"
      ]
    },
    "constraints": {
      "max_actions_per_hour": 100,
      "max_actions_per_day": 500,
      "require_human_approval": ["crm:delete"]
    },
    "metadata": {
      "contact": "support-team@acme.com",
      "documentation": "https://docs.acme.com/agents/support-bot"
    }
  }'
```

### Response

```json
{
  "manifest_id": "880e8400-e29b-41d4-a716-446655440003",
  "uapk_id": "customer-support-bot",
  "status": "pending",
  "manifest_hash": "sha256:a1b2c3d4e5f6...",
  "agent": {
    "id": "customer-support-bot",
    "name": "Customer Support Bot",
    "version": "1.0.0"
  },
  "capabilities": {
    "requested": ["email:send", "email:read", "crm:read", "crm:update"],
    "approved": []
  },
  "created_at": "2024-12-14T10:00:00Z"
}
```

---

## List Manifests

List all manifests in the organization.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/manifests`

### Request

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/manifests?status=active" \
  -H "Authorization: Bearer $TOKEN"
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter: `pending`, `active`, `suspended`, `revoked` |
| `team` | string | Filter by team |
| `limit` | integer | Max results (default 50) |
| `offset` | integer | Pagination offset |

### Response

```json
{
  "items": [
    {
      "manifest_id": "880e8400-e29b-41d4-a716-446655440003",
      "uapk_id": "customer-support-bot",
      "status": "active",
      "agent": {
        "name": "Customer Support Bot",
        "version": "1.0.0",
        "team": "support"
      },
      "capabilities_count": 4,
      "created_at": "2024-12-14T10:00:00Z",
      "approved_at": "2024-12-14T10:15:00Z"
    }
  ],
  "total": 1
}
```

---

## Get Manifest

Get full manifest details.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/manifests/{manifest_id}`

### Request

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/$MANIFEST_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Response

```json
{
  "manifest_id": "880e8400-e29b-41d4-a716-446655440003",
  "uapk_id": "customer-support-bot",
  "status": "active",
  "manifest_hash": "sha256:a1b2c3d4e5f6...",
  "agent": {
    "id": "customer-support-bot",
    "name": "Customer Support Bot",
    "version": "1.0.0",
    "description": "AI agent for handling customer inquiries",
    "organization": "acme-corp",
    "team": "support"
  },
  "capabilities": {
    "requested": ["email:send", "email:read", "crm:read", "crm:update"],
    "approved": ["email:send", "email:read", "crm:read", "crm:update"]
  },
  "constraints": {
    "max_actions_per_hour": 100,
    "max_actions_per_day": 500,
    "require_human_approval": ["crm:delete"]
  },
  "metadata": {
    "contact": "support-team@acme.com",
    "documentation": "https://docs.acme.com/agents/support-bot"
  },
  "approved_by": "admin@acme.com",
  "approved_at": "2024-12-14T10:15:00Z",
  "created_at": "2024-12-14T10:00:00Z"
}
```

---

## Approve Manifest

Approve a pending manifest.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/manifests/{manifest_id}/approve`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/$MANIFEST_ID/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approved_capabilities": [
      "email:send",
      "email:read",
      "crm:read"
    ],
    "notes": "Approved for customer support operations. CRM update pending security review."
  }'
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `approved_capabilities` | array | No | Subset of requested capabilities to approve (default: all) |
| `notes` | string | No | Approval notes for audit |

### Response

```json
{
  "manifest_id": "880e8400-e29b-41d4-a716-446655440003",
  "uapk_id": "customer-support-bot",
  "status": "active",
  "capabilities": {
    "requested": ["email:send", "email:read", "crm:read", "crm:update"],
    "approved": ["email:send", "email:read", "crm:read"]
  },
  "approved_by": "admin@acme.com",
  "approved_at": "2024-12-14T10:15:00Z",
  "notes": "Approved for customer support operations. CRM update pending security review."
}
```

---

## Reject Manifest

Reject a pending manifest.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/manifests/{manifest_id}/reject`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/$MANIFEST_ID/reject \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Requested capabilities exceed team authorization",
    "notes": "Please submit with reduced capability scope"
  }'
```

---

## Suspend Manifest

Temporarily suspend an active manifest.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/manifests/{manifest_id}/suspend`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/$MANIFEST_ID/suspend \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Security review required",
    "notes": "Suspended pending investigation of anomalous behavior"
  }'
```

### Response

```json
{
  "manifest_id": "880e8400-e29b-41d4-a716-446655440003",
  "uapk_id": "customer-support-bot",
  "status": "suspended",
  "suspended_by": "admin@acme.com",
  "suspended_at": "2024-12-14T12:00:00Z",
  "reason": "Security review required"
}
```

---

## Reactivate Manifest

Reactivate a suspended manifest.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/manifests/{manifest_id}/reactivate`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/$MANIFEST_ID/reactivate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Investigation complete, no issues found"
  }'
```

---

## Revoke Manifest

Permanently revoke a manifest.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/manifests/{manifest_id}/revoke`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/$MANIFEST_ID/revoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Agent decommissioned",
    "notes": "Agent replaced by v2.0"
  }'
```

!!! warning "Permanent Action"
    Revocation is permanent. The agent will need to register a new manifest.

---

## Get Manifest by UAPK ID

Look up a manifest by agent identifier.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/manifests/by-uapk/{uapk_id}`

### Request

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/by-uapk/customer-support-bot \
  -H "Authorization: Bearer $TOKEN"
```

---

## Validate Manifest

Validate a manifest without registering.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/manifests/validate`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/validate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.0",
    "agent": {
      "id": "test-agent",
      "name": "Test Agent",
      "version": "1.0.0"
    },
    "capabilities": {
      "requested": ["email:send"]
    }
  }'
```

### Response (Valid)

```json
{
  "valid": true,
  "manifest_hash": "sha256:x1y2z3...",
  "warnings": []
}
```

### Response (Invalid)

```json
{
  "valid": false,
  "errors": [
    {
      "field": "agent.id",
      "message": "Agent ID must be lowercase alphanumeric with hyphens"
    }
  ],
  "warnings": [
    {
      "field": "constraints",
      "message": "No rate limits defined, defaults will apply"
    }
  ]
}
```

---

## Manifest History

Get version history for a manifest.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/manifests/{manifest_id}/history`

### Request

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/$MANIFEST_ID/history \
  -H "Authorization: Bearer $TOKEN"
```

### Response

```json
{
  "items": [
    {
      "version": "1.0.1",
      "manifest_hash": "sha256:b2c3d4...",
      "status": "active",
      "changed_at": "2024-12-14T14:00:00Z",
      "changed_by": "admin@acme.com",
      "changes": ["Added crm:update capability"]
    },
    {
      "version": "1.0.0",
      "manifest_hash": "sha256:a1b2c3...",
      "status": "superseded",
      "changed_at": "2024-12-14T10:00:00Z",
      "changed_by": "admin@acme.com",
      "changes": ["Initial registration"]
    }
  ]
}
```

## Related

- [UAPK Manifest](../concepts/manifest.md) - Manifest concepts
- [Gateway API](gateway.md) - Using manifests for execution
- [Capability Tokens](../concepts/capabilities.md) - Token issuance

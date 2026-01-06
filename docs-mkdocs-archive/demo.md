---
title: Demo Walkthrough
description: Hands-on demonstration of UAPK Gateway
---

# Demo Walkthrough

This walkthrough demonstrates key UAPK Gateway features using a realistic scenario: a **Customer Support Bot** that needs to send emails and access a CRM system.

## Prerequisites

Start the gateway:

```bash
docker compose up -d
```

## Scenario

You're deploying an AI customer support agent that can:

- Send emails to customers
- Read customer records from CRM
- Update customer records

Some operations require human approval for safety.

!!! tip "Use Pre-Built 47er Templates"
    Instead of creating a custom manifest, you can load production-ready templates from our [47ers Library](47ers.md):

    ```bash
    # Load the "Outbound Email Guard" 47er
    python scripts/load_example_manifests.py --template=general/outbound_email_guard

    # Or load a legal settlement negotiation gate
    python scripts/load_example_manifests.py --template=legal/ip_enforcement_settlement_gate
    ```

    See `examples/47ers/` for all available templates.

## Step 1: Create Organization

```bash
# Create organization with admin user
curl -X POST http://localhost:8000/api/v1/orgs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "slug": "acme-corp",
    "admin_email": "admin@acme.com",
    "admin_password": "demo-password-123"
  }'
```

Save the `org_id` from the response:

```bash
export ORG_ID="550e8400-e29b-41d4-a716-446655440000"
```

## Step 2: Login

```bash
# Login to get access token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "demo-password-123"
  }' | jq '.access_token'
```

Save the token:

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Step 3: Create API Key

```bash
# Create API key for the agent
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "customer-support-bot-key",
    "scopes": ["gateway:execute", "gateway:evaluate"]
  }' | jq '.key'
```

Save the API key:

```bash
export API_KEY="ugw_live_..."
```

## Step 4: Register Manifest

Register the customer support agent manifest:

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
        "crm:update",
        "crm:delete"
      ]
    },
    "constraints": {
      "max_actions_per_hour": 100,
      "max_actions_per_day": 500,
      "require_human_approval": ["crm:delete"]
    },
    "metadata": {
      "contact": "support-team@acme.com"
    }
  }'
```

Save the manifest ID:

```bash
export MANIFEST_ID="880e8400-e29b-41d4-a716-446655440003"
```

## Step 5: Approve Manifest

```bash
# Approve the manifest
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/$MANIFEST_ID/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Approved for customer support operations"
  }'
```

## Step 6: Execute Actions

### 6.1 Allowed Action (Email Send)

```bash
# This action should be ALLOWED
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
        "body": "Thank you for contacting us. We have received your request."
      }
    }
  }' | jq '.decision, .result'
```

Expected output:

```json
"ALLOW"
{
  "success": true,
  "data": {
    "message_id": "msg-xyz789"
  }
}
```

### 6.2 Allowed Action (CRM Read)

```bash
# This action should be ALLOWED
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "agent_id": "customer-support-bot",
    "action": {
      "type": "crm",
      "tool": "read",
      "params": {
        "customer_id": "cust-12345"
      }
    }
  }' | jq '.decision'
```

### 6.3 Escalated Action (CRM Delete)

```bash
# This action should be ESCALATED (requires approval)
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "agent_id": "customer-support-bot",
    "action": {
      "type": "crm",
      "tool": "delete",
      "params": {
        "customer_id": "cust-12345"
      }
    }
  }' | jq '.decision, .approval_id'
```

Expected output:

```json
"ESCALATE"
"appr-xyz789"
```

Save the approval ID:

```bash
export APPROVAL_ID="appr-xyz789"
```

### 6.4 Denied Action (Unauthorized Tool)

```bash
# This action should be DENIED (tool not in manifest)
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "agent_id": "customer-support-bot",
    "action": {
      "type": "payment",
      "tool": "process",
      "params": {
        "amount": 100
      }
    }
  }' | jq '.decision, .reasons'
```

Expected output:

```json
"DENY"
[
  {
    "code": "ACTION_NOT_ALLOWED",
    "message": "Action type 'payment' is not permitted for this agent"
  }
]
```

## Step 7: Handle Approval

### View Pending Approval

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/$APPROVAL_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

### Approve the Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/$APPROVAL_ID/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Verified customer requested deletion per GDPR request"
  }' | jq '.status, .execution_result'
```

Expected output:

```json
"approved"
{
  "success": true,
  "data": {
    "deleted": true
  }
}
```

## Step 8: View Audit Trail

### List Recent Logs

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/logs?uapk_id=customer-support-bot&limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq '.items[] | {record_id, action_type, tool, decision}'
```

Expected output:

```json
{"record_id": "int-004", "action_type": "crm", "tool": "delete", "decision": "approved"}
{"record_id": "int-003", "action_type": "payment", "tool": "process", "decision": "denied"}
{"record_id": "int-002", "action_type": "crm", "tool": "read", "decision": "approved"}
{"record_id": "int-001", "action_type": "email", "tool": "send", "decision": "approved"}
```

### Verify Chain Integrity

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/logs/verify/customer-support-bot \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

Expected output:

```json
{
  "is_valid": true,
  "record_count": 4,
  "first_record_id": "int-001",
  "last_record_id": "int-004",
  "errors": []
}
```

## Step 9: Export Logs

```bash
# Export logs for compliance
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/logs/export/download \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "include_manifest": true
  }' > demo-export.json

# Verify offline
python scripts/verify_log_chain.py demo-export.json
```

## Summary

In this demo, you:

1. **Created an organization** and admin user
2. **Registered an agent manifest** with capabilities and constraints
3. **Executed actions** and saw:
   - ✅ **ALLOW**: email:send, crm:read
   - ⏳ **ESCALATE**: crm:delete (required approval)
   - ❌ **DENY**: payment:process (not authorized)
4. **Approved a request** through the operator workflow
5. **Verified the audit trail** with hash-chained records

## Next Steps

- [47ers Library](47ers.md) - Pre-built templates for legal, finance, and compliance workflows
- [Quickstart](quickstart.md) - Full setup guide
- [API Reference](api/index.md) - Complete API docs
- [Operator Guide](operator/index.md) - Managing approvals
- [Concepts](concepts/index.md) - Architecture deep dive

## Cleanup

```bash
docker compose down -v
```

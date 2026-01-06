# Core Concepts

Understanding the key abstractions in UAPK Gateway.

## UAPK Manifest

A JSON document that declares an agent's identity and requested capabilities.

```json
{
  "$schema": "https://uapk.dev/schemas/manifest.v1.json",
  "version": "1.0",
  "agent": {
    "id": "agent-001",
    "name": "Customer Support Bot",
    "version": "1.0.0",
    "organization": "org-acme"
  },
  "capabilities": {
    "requested": [
      "email:send",
      "crm:read",
      "crm:update"
    ]
  },
  "constraints": {
    "max_actions_per_hour": 100,
    "require_human_approval": ["crm:delete"]
  }
}
```

## Capability Token

A time-limited, signed token that grants specific permissions to an agent.

- **Issued** by operators or automated systems
- **Scoped** to specific capabilities
- **Expires** after a configured duration
- **Revocable** at any time

```json
{
  "token_id": "cap-xyz789",
  "agent_id": "agent-001",
  "capabilities": ["email:send", "crm:read"],
  "issued_at": "2024-01-15T10:00:00Z",
  "expires_at": "2024-01-15T22:00:00Z",
  "constraints": {
    "max_actions": 50
  }
}
```

## Action Request

When an agent wants to perform an action, it submits a request:

```json
{
  "action": "email:send",
  "parameters": {
    "to": "customer@example.com",
    "subject": "Your order has shipped",
    "body": "..."
  },
  "context": {
    "conversation_id": "conv-123",
    "reason": "Customer requested shipping update"
  }
}
```

## InteractionRecord

Every action request creates an immutable audit record:

```json
{
  "record_id": "ir-abc123",
  "timestamp": "2024-01-15T14:30:00Z",
  "agent_id": "agent-001",
  "action": "email:send",
  "request": { ... },
  "decision": "approved",
  "result": { "success": true, "message_id": "msg-xyz" },
  "policy_evaluations": [
    { "policy": "rate-limit", "result": "pass" },
    { "policy": "capability-check", "result": "pass" }
  ],
  "signature": "...",
  "previous_hash": "..."
}
```

Key properties:
- **Signed**: Cryptographic signature prevents tampering
- **Chained**: Each record includes hash of previous record
- **Complete**: Includes request, decision, and result

## Policy

Rules that govern agent behavior:

```yaml
name: rate-limit-emails
description: Limit email sending rate
scope:
  agents: ["agent-*"]
  actions: ["email:send"]
rules:
  - type: rate_limit
    max: 10
    period: 1h
  - type: require_approval
    when:
      recipients_count: ">5"
```

Policy types:
- **Rate Limits**: Max actions per time period
- **Budget Limits**: Max cost/tokens per period
- **Capability Restrictions**: Limit what actions are allowed
- **Approval Workflows**: Require human approval
- **Time Restrictions**: Only allow during certain hours

## Organization Hierarchy

```
Organization (org-acme)
├── Team (engineering)
│   ├── Agent (code-review-bot)
│   └── Agent (deployment-bot)
└── Team (support)
    ├── Agent (ticket-triage-bot)
    └── Agent (customer-response-bot)
```

- **Organizations**: Top-level tenant
- **Teams**: Group agents with shared policies
- **Agents**: Individual AI systems with manifests

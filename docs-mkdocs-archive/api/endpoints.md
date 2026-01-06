# API Endpoints

Complete reference for UAPK Gateway API endpoints.

## Health Checks

### GET /healthz

Liveness probe for load balancers.

```bash
curl http://localhost:8000/healthz
```

Response:
```json
{"status": "ok"}
```

### GET /readyz

Readiness probe checking dependencies.

```bash
curl http://localhost:8000/readyz
```

Response:
```json
{
  "status": "ready",
  "checks": {
    "database": true
  }
}
```

## Gateway Endpoints

See [Gateway API](gateway.md) for complete documentation.

### POST /api/v1/gateway/execute

Execute an agent action through the gateway.

**Headers:**
- `X-API-Key`: Agent API key (required)

**Request:**
```json
{
  "uapk_id": "my-agent",
  "agent_id": "my-agent",
  "action": {
    "type": "email",
    "tool": "send",
    "params": {
      "to": "user@example.com",
      "subject": "Hello",
      "body": "World"
    }
  },
  "capability_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9..."
}
```

**Response (Allowed):**
```json
{
  "interaction_id": "int-abc123",
  "decision": "allow",
  "executed": true,
  "result": {
    "success": true,
    "data": {
      "message_id": "msg-xyz"
    }
  }
}
```

**Response (Denied):**
```json
{
  "interaction_id": "int-abc124",
  "decision": "deny",
  "executed": false,
  "reasons": [
    {
      "code": "BUDGET_EXCEEDED",
      "message": "Daily email budget exceeded"
    }
  ]
}
```

### POST /api/v1/gateway/evaluate

Evaluate an action without executing (dry-run).

See [Gateway API](gateway.md) for details.

## Manifests

See [Manifests API](manifests.md) for complete documentation.

## Agents (Future)

### GET /api/v1/agents

List registered agents.

### POST /api/v1/agents

Register a new agent.

### GET /api/v1/agents/{id}

Get agent details.

### DELETE /api/v1/agents/{id}

Deactivate an agent.

## Policies (Coming in v0.2)

### GET /api/v1/policies

List policies.

### POST /api/v1/policies

Create a new policy.

### PUT /api/v1/policies/{id}

Update a policy.

### DELETE /api/v1/policies/{id}

Delete a policy.

## Interaction Records (Coming in v0.2)

### GET /api/v1/records

List interaction records with filtering.

**Query Parameters:**
- `agent_id`: Filter by agent
- `action`: Filter by action type
- `status`: `approved` or `denied`
- `from`: Start timestamp
- `to`: End timestamp
- `limit`: Max results (default 100)
- `offset`: Pagination offset

### GET /api/v1/records/{id}

Get a specific interaction record.

### GET /api/v1/records/{id}/verify

Verify record signature and chain integrity.

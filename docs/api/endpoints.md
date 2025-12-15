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

## Actions (Coming in v0.2)

### POST /api/v1/actions

Submit an action request.

**Headers:**
- `X-API-Key`: Agent API key (required)
- `X-Capability-Token`: Capability token (required)

**Request:**
```json
{
  "action": "email:send",
  "parameters": {
    "to": "user@example.com",
    "subject": "Hello",
    "body": "World"
  },
  "context": {
    "reason": "User requested notification"
  }
}
```

**Response (Approved):**
```json
{
  "status": "approved",
  "interaction_record_id": "ir-abc123",
  "result": {
    "success": true,
    "message_id": "msg-xyz"
  }
}
```

**Response (Denied):**
```json
{
  "status": "denied",
  "interaction_record_id": "ir-abc124",
  "reason": "Rate limit exceeded",
  "policy": "rate-limit-emails"
}
```

## Agents (Coming in v0.2)

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

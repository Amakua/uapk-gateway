---
title: Authentication
description: API authentication methods and examples
---

# Authentication

The UAPK Gateway supports two authentication methods depending on your use case.

## Authentication Methods

| Method | Header | Use Case |
|--------|--------|----------|
| Bearer Token | `Authorization: Bearer <token>` | Dashboard, admin operations |
| API Key | `X-API-Key: <key>` | Agent integrations, programmatic access |

## User Authentication (Bearer Token)

For dashboard access and administrative operations, use bearer token authentication.

### Create Organization & Admin User

```bash
# Create a new organization with admin user
curl -X POST http://localhost:8000/api/v1/orgs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "slug": "acme-corp",
    "admin_email": "admin@acme.com",
    "admin_password": "secure-password-here"
  }'
```

Response:

```json
{
  "org_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "admin_user": {
    "user_id": "660e8400-e29b-41d4-a716-446655440001",
    "email": "admin@acme.com",
    "role": "admin"
  },
  "created_at": "2024-12-14T10:00:00Z"
}
```

### Login

```bash
# Login to get access token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "secure-password-here"
  }'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "user_id": "660e8400-e29b-41d4-a716-446655440001",
    "email": "admin@acme.com",
    "org_id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "admin"
  }
}
```

### Using the Token

```bash
# Store token for subsequent requests
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export ORG_ID="550e8400-e29b-41d4-a716-446655440000"

# Use token in requests
curl http://localhost:8000/api/v1/orgs/$ORG_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Token Refresh

Tokens expire after 1 hour. Refresh before expiry:

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer $TOKEN"
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Logout

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

## API Key Authentication

For agent integrations and programmatic access, use API keys.

### Create API Key

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production-agent-key",
    "description": "API key for production agents",
    "scopes": ["gateway:execute", "logs:read"],
    "expires_in_days": 90
  }'
```

Response:

```json
{
  "key_id": "key-abc123",
  "name": "production-agent-key",
  "key": "ugw_live_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456",
  "scopes": ["gateway:execute", "logs:read"],
  "expires_at": "2025-03-14T10:00:00Z",
  "created_at": "2024-12-14T10:00:00Z"
}
```

!!! warning "Save the Key"
    The full API key is only shown once. Store it securely.

### Using API Keys

```bash
# Store API key
export API_KEY="ugw_live_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456"

# Use in gateway requests
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "my-agent",
    "agent_id": "my-agent",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {
        "to": "user@example.com",
        "subject": "Hello"
      }
    }
  }'
```

### API Key Scopes

| Scope | Description |
|-------|-------------|
| `gateway:execute` | Execute actions via gateway |
| `gateway:evaluate` | Evaluate actions (dry-run) |
| `manifests:read` | Read manifests |
| `manifests:write` | Create/update manifests |
| `logs:read` | Read audit logs |
| `logs:export` | Export audit logs |
| `approvals:read` | Read approvals |
| `approvals:write` | Approve/deny requests |

### List API Keys

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/api-keys \
  -H "Authorization: Bearer $TOKEN"
```

Response:

```json
{
  "items": [
    {
      "key_id": "key-abc123",
      "name": "production-agent-key",
      "key_prefix": "ugw_live_aBcD...",
      "scopes": ["gateway:execute", "logs:read"],
      "last_used_at": "2024-12-14T09:30:00Z",
      "expires_at": "2025-03-14T10:00:00Z"
    }
  ],
  "total": 1
}
```

### Revoke API Key

```bash
curl -X DELETE http://localhost:8000/api/v1/orgs/$ORG_ID/api-keys/key-abc123 \
  -H "Authorization: Bearer $TOKEN"
```

## Capability Tokens

Capability tokens provide additional authorization for specific actions. They are Ed25519-signed JWTs.

### Include with Requests

```bash
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "my-agent",
    "agent_id": "my-agent",
    "capability_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {...}
    }
  }'
```

See [Capability Tokens](../concepts/capabilities.md) for details on issuing tokens.

## Security Best Practices

!!! tip "Use Environment Variables"
    Never hardcode tokens or API keys in scripts:
    ```bash
    export UAPK_API_KEY=$(cat ~/.uapk/api-key)
    ```

!!! tip "Minimal Scopes"
    Grant only the scopes needed for the specific use case.

!!! tip "Short Expiry for Tokens"
    Use short-lived bearer tokens (1 hour) and refresh as needed.

!!! tip "Rotate API Keys"
    Rotate API keys regularly, especially after team changes.

!!! warning "HTTPS Required"
    Always use HTTPS in production to protect credentials in transit.

## Error Responses

### Invalid Token

```json
{
  "detail": {
    "code": "INVALID_TOKEN",
    "message": "The provided token is invalid or expired"
  }
}
```

### Missing Authentication

```json
{
  "detail": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "This endpoint requires authentication"
  }
}
```

### Insufficient Permissions

```json
{
  "detail": {
    "code": "FORBIDDEN",
    "message": "You do not have permission to perform this action"
  }
}
```

## Related

- [Organizations](organizations.md) - Creating orgs and users
- [Gateway](gateway.md) - Using API keys for agent execution
- [Capability Tokens](../concepts/capabilities.md) - Token issuance

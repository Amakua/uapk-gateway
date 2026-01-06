---
title: API Reference
description: Complete REST API documentation for UAPK Gateway
---

# API Reference

The UAPK Gateway exposes a RESTful API for managing organizations, manifests, tokens, and action execution.

## Base URL

```
http://localhost:8000/api/v1
```

For production deployments, use HTTPS:

```
https://gateway.yourdomain.com/api/v1
```

## Authentication

The API supports two authentication methods:

| Method | Use Case | Header |
|--------|----------|--------|
| **Bearer Token** | Dashboard, admin operations | `Authorization: Bearer <token>` |
| **API Key** | Agent integrations | `X-API-Key: <key>` |

See [Authentication](authentication.md) for details.

## Content Type

All requests and responses use JSON:

```bash
-H "Content-Type: application/json"
```

## API Sections

<div class="grid cards" markdown>

-   :material-account-group: **Organizations & Users**

    ---

    Manage organizations, users, and roles

    [:octicons-arrow-right-24: Organizations](organizations.md)

-   :material-file-document: **Manifests**

    ---

    Register and manage agent manifests

    [:octicons-arrow-right-24: Manifests](manifests.md)

-   :material-shield-check: **Gateway**

    ---

    Evaluate and execute agent actions

    [:octicons-arrow-right-24: Gateway](gateway.md)

-   :material-check-circle: **Approvals**

    ---

    Manage human-in-the-loop approvals

    [:octicons-arrow-right-24: Approvals](approvals.md)

-   :material-clipboard-list: **Logs**

    ---

    Query and export audit logs

    [:octicons-arrow-right-24: Logs](logs.md)

</div>

## Common Patterns

### Pagination

List endpoints support pagination:

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/logs?limit=50&offset=100" \
  -H "Authorization: Bearer $TOKEN"
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Maximum items to return |
| `offset` | integer | 0 | Number of items to skip |

### Filtering

Many endpoints support filtering:

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/logs?uapk_id=my-agent&decision=approved" \
  -H "Authorization: Bearer $TOKEN"
```

### Error Responses

Errors return a consistent structure:

```json
{
  "detail": {
    "code": "MANIFEST_NOT_FOUND",
    "message": "No manifest found for agent 'unknown-agent'"
  }
}
```

| HTTP Code | Meaning |
|-----------|---------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing or invalid auth |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation failed |
| 500 | Internal Server Error |

### Rate Limiting

The API implements rate limiting per API key:

| Tier | Requests/minute | Requests/day |
|------|-----------------|--------------|
| Free | 60 | 10,000 |
| Pro | 600 | 100,000 |
| Enterprise | Unlimited | Unlimited |

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 55
X-RateLimit-Reset: 1702560000
```

## Quick Reference

### Organizations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orgs` | Create organization |
| GET | `/orgs/{org_id}` | Get organization |
| PATCH | `/orgs/{org_id}` | Update organization |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orgs/{org_id}/users` | Create user |
| GET | `/orgs/{org_id}/users` | List users |
| POST | `/auth/login` | Login |
| POST | `/auth/logout` | Logout |

### API Keys

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orgs/{org_id}/api-keys` | Create API key |
| GET | `/orgs/{org_id}/api-keys` | List API keys |
| DELETE | `/orgs/{org_id}/api-keys/{key_id}` | Revoke API key |

### Manifests

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/orgs/{org_id}/manifests` | Register manifest |
| GET | `/orgs/{org_id}/manifests` | List manifests |
| GET | `/orgs/{org_id}/manifests/{manifest_id}` | Get manifest |
| POST | `/orgs/{org_id}/manifests/{manifest_id}/approve` | Approve manifest |
| POST | `/orgs/{org_id}/manifests/{manifest_id}/suspend` | Suspend manifest |

### Gateway

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/gateway/evaluate` | Evaluate action (dry-run) |
| POST | `/gateway/execute` | Execute action |

### Approvals

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orgs/{org_id}/approvals` | List approvals |
| GET | `/orgs/{org_id}/approvals/{approval_id}` | Get approval |
| POST | `/orgs/{org_id}/approvals/{approval_id}/approve` | Approve request |
| POST | `/orgs/{org_id}/approvals/{approval_id}/deny` | Deny request |

### Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orgs/{org_id}/logs` | List logs |
| GET | `/orgs/{org_id}/logs/{record_id}` | Get log record |
| GET | `/orgs/{org_id}/logs/verify/{uapk_id}` | Verify chain |
| POST | `/orgs/{org_id}/logs/export/download` | Export logs (JSON) |
| POST | `/orgs/{org_id}/logs/export/jsonl` | Export logs (JSONL) |

## SDKs

Official SDKs are available for common languages:

=== "Python"

    ```bash
    pip install uapk-gateway
    ```

    ```python
    from uapk_gateway import GatewayClient

    client = GatewayClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )

    result = client.execute(
        uapk_id="my-agent",
        action_type="email",
        tool="send",
        params={"to": "user@example.com", "subject": "Hello"}
    )
    ```

=== "TypeScript"

    ```bash
    npm install @uapk/gateway-client
    ```

    ```typescript
    import { GatewayClient } from '@uapk/gateway-client';

    const client = new GatewayClient({
      baseUrl: 'http://localhost:8000',
      apiKey: 'your-api-key',
    });

    const result = await client.execute({
      uapkId: 'my-agent',
      actionType: 'email',
      tool: 'send',
      params: { to: 'user@example.com', subject: 'Hello' },
    });
    ```

## OpenAPI Specification

The full OpenAPI specification is available at:

```
http://localhost:8000/openapi.json
```

Interactive documentation (Swagger UI):

```
http://localhost:8000/docs
```

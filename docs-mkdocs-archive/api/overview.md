# API Overview

UAPK Gateway exposes a RESTful API for agents and operators.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

### For Agents

Include the API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:8000/api/v1/gateway/execute
```

### For Operators

Include the JWT bearer token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer your-jwt-token" \
  http://localhost:8000/api/v1/orgs/{org_id}/approvals
```

## Response Format

All responses are JSON:

```json
{
  "data": { ... },
  "meta": {
    "request_id": "req-123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

Error responses:

```json
{
  "error": {
    "code": "POLICY_VIOLATION",
    "message": "Rate limit exceeded",
    "details": {
      "limit": 10,
      "period": "1h",
      "current": 11
    }
  }
}
```

## Versioning

The API is versioned via URL path:

- `/api/v1/...` - Current stable version

Breaking changes will increment the version number.

## Rate Limiting

Default limits (configurable per organization):

- 1000 requests/minute for operators
- Agent limits defined by policies

Rate limit headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1705312200
```

## Interactive Documentation

- **Swagger UI**: [/docs](/docs)
- **ReDoc**: [/redoc](/redoc)
- **OpenAPI Spec**: [/openapi.json](/openapi.json)

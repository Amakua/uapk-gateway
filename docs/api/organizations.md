---
title: Organizations API
description: Manage organizations and users
---

# Organizations API

Manage organizations, users, and team structure.

## Create Organization

Create a new organization with an admin user.

<div class="api-method post">POST</div> `/api/v1/orgs`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "slug": "acme-corp",
    "admin_email": "admin@acme.com",
    "admin_password": "secure-password-here"
  }'
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Organization display name |
| `slug` | string | Yes | URL-friendly identifier |
| `admin_email` | string | Yes | Admin user email |
| `admin_password` | string | Yes | Admin user password (min 8 chars) |

### Response

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

---

## Get Organization

Retrieve organization details.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}`

### Request

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Response

```json
{
  "org_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "settings": {
    "approval_expiry_hours": 24,
    "default_rate_limit": 100
  },
  "created_at": "2024-12-14T10:00:00Z",
  "updated_at": "2024-12-14T10:00:00Z"
}
```

---

## Update Organization

Update organization settings.

<div class="api-method patch">PATCH</div> `/api/v1/orgs/{org_id}`

### Request

```bash
curl -X PATCH http://localhost:8000/api/v1/orgs/$ORG_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "settings": {
      "approval_expiry_hours": 48
    }
  }'
```

### Response

```json
{
  "org_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corporation",
  "slug": "acme-corp",
  "settings": {
    "approval_expiry_hours": 48,
    "default_rate_limit": 100
  },
  "updated_at": "2024-12-14T11:00:00Z"
}
```

---

## Create User

Add a new user to the organization.

<div class="api-method post">POST</div> `/api/v1/orgs/{org_id}/users`

### Request

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "operator@acme.com",
    "password": "secure-password",
    "role": "operator",
    "name": "Jane Smith"
  }'
```

### Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | User email address |
| `password` | string | Yes | User password (min 8 chars) |
| `role` | string | Yes | One of: `admin`, `operator`, `viewer` |
| `name` | string | No | User display name |

### User Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access, manage users and settings |
| `operator` | Approve/deny requests, view logs |
| `viewer` | Read-only access to logs and approvals |

### Response

```json
{
  "user_id": "770e8400-e29b-41d4-a716-446655440002",
  "email": "operator@acme.com",
  "name": "Jane Smith",
  "role": "operator",
  "org_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-12-14T10:30:00Z"
}
```

---

## List Users

List all users in the organization.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/users`

### Request

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/users?role=operator" \
  -H "Authorization: Bearer $TOKEN"
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `role` | string | Filter by role |
| `limit` | integer | Max results (default 50) |
| `offset` | integer | Pagination offset |

### Response

```json
{
  "items": [
    {
      "user_id": "660e8400-e29b-41d4-a716-446655440001",
      "email": "admin@acme.com",
      "name": "Admin User",
      "role": "admin",
      "last_login_at": "2024-12-14T09:00:00Z"
    },
    {
      "user_id": "770e8400-e29b-41d4-a716-446655440002",
      "email": "operator@acme.com",
      "name": "Jane Smith",
      "role": "operator",
      "last_login_at": "2024-12-14T08:30:00Z"
    }
  ],
  "total": 2
}
```

---

## Get User

Get a specific user.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/users/{user_id}`

### Request

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/users/$USER_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## Update User

Update user details or role.

<div class="api-method patch">PATCH</div> `/api/v1/orgs/{org_id}/users/{user_id}`

### Request

```bash
curl -X PATCH http://localhost:8000/api/v1/orgs/$ORG_ID/users/$USER_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin",
    "name": "Jane Smith-Jones"
  }'
```

---

## Delete User

Remove a user from the organization.

<div class="api-method delete">DELETE</div> `/api/v1/orgs/{org_id}/users/{user_id}`

### Request

```bash
curl -X DELETE http://localhost:8000/api/v1/orgs/$ORG_ID/users/$USER_ID \
  -H "Authorization: Bearer $TOKEN"
```

### Response

```json
{
  "deleted": true,
  "user_id": "770e8400-e29b-41d4-a716-446655440002"
}
```

---

## Organization Statistics

Get organization usage statistics.

<div class="api-method get">GET</div> `/api/v1/orgs/{org_id}/stats`

### Request

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/stats?from=2024-12-01&to=2024-12-14" \
  -H "Authorization: Bearer $TOKEN"
```

### Response

```json
{
  "period": {
    "from": "2024-12-01T00:00:00Z",
    "to": "2024-12-14T23:59:59Z"
  },
  "manifests": {
    "total": 5,
    "active": 4,
    "pending": 1
  },
  "actions": {
    "total": 1250,
    "allowed": 1180,
    "denied": 45,
    "escalated": 25
  },
  "approvals": {
    "pending": 3,
    "approved": 20,
    "denied": 2,
    "expired": 0
  }
}
```

## Related

- [Authentication](authentication.md) - Login and tokens
- [Manifests](manifests.md) - Agent registration

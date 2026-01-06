---
title: Quickstart
description: Get UAPK Gateway running in 5 minutes
---

# Quickstart

Get UAPK Gateway running locally in 5 minutes using Docker Compose.

!!! info "Commercial Option Available"
    Want expert help? Our [Agent Governance Pilot](business/pilot.md) delivers a production-ready deployment in 2-4 weeks ($15,000 - $25,000).

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) v2+
- [Git](https://git-scm.com/)

## 1. Clone and Start

```bash
# Clone the repository
git clone https://github.com/UAPK/gateway.git
cd gateway

# Copy environment file
cp .env.example .env

# Start the containers
make dev
```

This starts:

- **PostgreSQL** database on port 5432
- **UAPK Gateway** backend on port 8000

## 2. Initialize the Database

```bash
# Run database migrations
make migrate

# Create admin user and demo organization
make bootstrap
```

The bootstrap creates:

- **Admin user**: `admin@example.com` / `admin123`
- **Demo organization**: `demo-org`

## 3. Access the Dashboard

Open [http://localhost:8000](http://localhost:8000) and login with the admin credentials.

!!! tip "API Documentation"
    Interactive API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs)

## 4. Get an API Key

=== "Via Dashboard"

    1. Navigate to **API Keys** in the sidebar
    2. Click **Create API Key**
    3. Copy the generated key (shown only once)

=== "Via API"

    ```bash
    # Login to get JWT token
    TOKEN=$(curl -s http://localhost:8000/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d '{"email":"admin@example.com","password":"admin123"}' \
      | jq -r '.access_token')

    # Get your organization ID
    ORG_ID=$(curl -s http://localhost:8000/api/v1/users/me \
      -H "Authorization: Bearer $TOKEN" \
      | jq -r '.default_org_id')

    # Create API key
    curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/api-keys \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"name": "dev-key", "scopes": ["gateway:execute", "logs:read"]}'
    ```

## 5. Register a Manifest

Create a manifest file `my-agent.json`:

```json
{
  "$schema": "https://uapk.dev/schemas/manifest.v1.json",
  "version": "1.0",
  "agent": {
    "id": "my-first-agent",
    "name": "My First Agent",
    "version": "1.0.0",
    "description": "A demo agent for testing UAPK Gateway"
  },
  "capabilities": {
    "requested": [
      "email:send",
      "calendar:read"
    ]
  },
  "constraints": {
    "max_actions_per_hour": 50
  }
}
```

Register it:

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/manifests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @my-agent.json
```

## 6. Execute an Action

```bash
# Using API key
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "my-first-agent",
    "agent_id": "my-first-agent",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {
        "to": "user@example.com",
        "subject": "Hello from UAPK",
        "body": "This is a test email."
      }
    }
  }'
```

Response:

```json
{
  "interaction_id": "int-abc123def456",
  "decision": "ALLOW",
  "executed": true,
  "result": {
    "success": true,
    "data": {"message_id": "msg-789"}
  },
  "timestamp": "2024-12-14T10:30:00Z"
}
```

## 7. View the Audit Log

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/logs \
  -H "Authorization: Bearer $TOKEN"
```

Or view in the dashboard at **Logs**.

---

## What's Next?

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
### :material-book-open-variant: [Concepts](concepts/index.md)
Understand manifests, capabilities, policies, and audit logs.
</div>

<div class="feature-card" markdown>
### :material-api: [API Reference](api/index.md)
Complete API documentation with examples.
</div>

<div class="feature-card" markdown>
### :material-account-check: [Approvals](concepts/approvals.md)
Set up human-in-the-loop approval workflows.
</div>

<div class="feature-card" markdown>
### :material-rocket: [Deployment](deployment/index.md)
Deploy to production on a single VM.
</div>

</div>

## Troubleshooting

??? question "Containers won't start"

    Check if ports 5432 or 8000 are already in use:
    ```bash
    lsof -i :5432
    lsof -i :8000
    ```

    View container logs:
    ```bash
    make logs
    ```

??? question "Database connection errors"

    Wait a few seconds for PostgreSQL to be ready, then retry:
    ```bash
    make migrate
    ```

    Or reset everything:
    ```bash
    make db-reset
    make migrate
    make bootstrap
    ```

??? question "API returns 401 Unauthorized"

    - Check your API key is correct
    - Ensure the key has the required scopes
    - For JWT: verify the token hasn't expired

---

## Clean Up

```bash
# Stop containers
make stop

# Stop and remove volumes (deletes all data)
docker compose down -v
```

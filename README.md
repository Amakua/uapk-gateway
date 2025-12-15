# UAPK Gateway

**Universal Agent Protocol Kit Gateway** - Policy enforcement and audit logging for AI agents.

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Make (optional, for convenience commands)

### 1. Start the Development Environment

```bash
# Clone and enter the repository
cd uapk-gateway

# Start all services
make dev
# or: docker compose up -d
```

### 2. Run Database Migrations

```bash
make migrate
# or: docker compose run --rm migrate
```

### 3. Create Admin User and Organization

```bash
make bootstrap
# or: docker compose run --rm bootstrap
```

This creates:
- **Admin user**: `admin@example.com` / `changeme123`
- **Organization**: "Default Organization" (slug: `default`)

You can customize these with environment variables:

```bash
ADMIN_EMAIL=admin@mycompany.com \
ADMIN_PASSWORD=secure-password-here \
ORG_NAME="My Company" \
ORG_SLUG=mycompany \
make bootstrap
```

### 4. Access the Gateway

- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Login**: Use the admin credentials from step 3

## Authentication

### Human Users (JWT)

Login via the UI or API:

```bash
# Login to get a JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "changeme123"}'

# Response:
# {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 86400}

# Use the token for authenticated requests
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJ..."
```

### Machine Clients (API Keys)

Create an API key for agent authentication:

```bash
# Create an API key (requires JWT auth)
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"name": "My Agent Key", "org_id": "your-org-uuid"}'

# Response (key shown ONLY ONCE):
# {"id": "...", "key": "uapk_abc123...", "key_prefix": "uapk_abc123", ...}

# Use API key for agent requests
curl http://localhost:8000/api/v1/healthz \
  -H "X-API-Key: uapk_abc123..."
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login with email/password
- `GET /api/v1/auth/me` - Get current user info

### Organizations
- `POST /api/v1/orgs` - Create organization
- `GET /api/v1/orgs` - List user's organizations
- `GET /api/v1/orgs/{id}` - Get organization details

### Users
- `POST /api/v1/users` - Create user
- `GET /api/v1/users` - List users

### Memberships
- `POST /api/v1/orgs/{id}/memberships` - Add user to org
- `GET /api/v1/orgs/{id}/memberships` - List org members
- `DELETE /api/v1/orgs/{id}/memberships/{id}` - Remove member

### API Keys
- `POST /api/v1/api-keys` - Create API key
- `GET /api/v1/api-keys` - List API keys
- `POST /api/v1/api-keys/{id}/revoke` - Revoke API key

### Health
- `GET /healthz` - Liveness probe
- `GET /readyz` - Readiness probe

## Development

### Running Tests

```bash
# Run tests in Docker
make test

# Run with coverage
make test-cov
```

### Code Quality

```bash
# Lint
make lint

# Format
make format

# Type check
make typecheck

# Run all checks
make check
```

### Database Commands

```bash
# Open PostgreSQL shell
make db-shell

# Reset database (destroys all data)
make db-reset
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | (dev key) | JWT signing secret (CHANGE IN PRODUCTION) |
| `DATABASE_URL` | (local postgres) | PostgreSQL connection URL |
| `ADMIN_EMAIL` | `admin@example.com` | Bootstrap admin email |
| `ADMIN_PASSWORD` | `changeme123` | Bootstrap admin password |
| `ORG_NAME` | `Default Organization` | Bootstrap organization name |
| `ORG_SLUG` | `default` | Bootstrap organization slug |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
| `JWT_EXPIRATION_MINUTES` | `1440` (24h) | JWT token expiration |

## Security Notes

- **Change the SECRET_KEY** in production
- **Change the default admin password** after first login
- API keys are hashed - full key shown only at creation
- Use HTTPS in production (via Caddy or other reverse proxy)

## Architecture

- **Backend**: Python 3.12 + FastAPI
- **Database**: PostgreSQL 16
- **UI**: Server-rendered with Jinja2 + HTMX
- **Auth**: JWT for humans, API keys for machines

## License

Apache License 2.0

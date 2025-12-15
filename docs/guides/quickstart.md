# Quickstart

Get UAPK Gateway running in under 5 minutes.

## Prerequisites

- Docker and Docker Compose
- Git

## Installation

```bash
# Clone the repository
git clone https://github.com/example/uapk-gateway.git
cd uapk-gateway

# Copy example environment
cp .env.example .env

# Start services
make dev
```

## Verify Installation

Check that services are running:

```bash
# Health check
curl http://localhost:8000/healthz
# Expected: {"status":"ok"}

# Readiness check
curl http://localhost:8000/readyz
# Expected: {"status":"ready","checks":{"database":true}}
```

## Access the Dashboard

Open [http://localhost:8000](http://localhost:8000) in your browser to access the operator dashboard.

## API Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Next Steps

1. [Configure your first organization](configuration.md)
2. [Register an agent](agent-integration.md)
3. [Set up policies](policies.md)

## Troubleshooting

### Services won't start

```bash
# Check logs
docker compose logs

# Rebuild containers
make rebuild
```

### Database connection errors

```bash
# Check postgres is healthy
docker compose ps postgres

# Reset database
make db-reset
```

### Port conflicts

Edit `.env` to change ports:

```env
BACKEND_PORT=8001
POSTGRES_PORT=5433
```

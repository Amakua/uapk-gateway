# Installation

Detailed installation instructions for UAPK Gateway.

## System Requirements

- **OS**: Linux (recommended), macOS, or Windows with WSL2
- **Docker**: 24.0+
- **Docker Compose**: v2.20+
- **Memory**: 2GB minimum, 4GB recommended
- **Disk**: 10GB minimum

## Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/example/uapk-gateway.git
cd uapk-gateway
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` as needed:

```env
# Required for production
SECRET_KEY=your-secure-random-key

# Optional: Change ports
BACKEND_PORT=8000
POSTGRES_PORT=5432
```

### 3. Start Services

```bash
make dev
```

This starts:
- Backend API on port 8000
- PostgreSQL on port 5432

### 4. Verify

```bash
curl http://localhost:8000/healthz
```

## Production Deployment

See [Deployment Guide](deployment.md) for production setup with:
- TLS/HTTPS via Caddy
- Systemd service management
- Security hardening
- Backup procedures

## Local Development (Without Docker)

For contributors who want to run without Docker:

### Prerequisites

- Python 3.12+
- PostgreSQL 16
- uv or pip

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/uapk

# Run migrations (when available)
# alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

## Updating

```bash
# Pull latest changes
git pull

# Rebuild containers
make rebuild

# Run migrations (when available)
# make migrate
```

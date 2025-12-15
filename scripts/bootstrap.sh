#!/usr/bin/env bash
# Bootstrap script for UAPK Gateway development environment
set -euo pipefail

echo "=== UAPK Gateway Bootstrap ==="
echo ""

# Check prerequisites
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: $1 is required but not installed."
        exit 1
    fi
}

echo "Checking prerequisites..."
check_command docker
check_command git

# Check Docker Compose (v2)
if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose v2 is required."
    echo "Please install Docker Desktop or docker-compose-plugin."
    exit 1
fi

echo "  - docker: $(docker --version)"
echo "  - docker compose: $(docker compose version --short)"
echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "  Created .env file"
else
    echo "  .env already exists, skipping"
fi

# Generate a secret key if using default
if grep -q "dev-secret-key-change-in-production" .env 2>/dev/null; then
    echo ""
    echo "WARNING: Using default SECRET_KEY."
    echo "For production, generate a secure key:"
    echo "  openssl rand -hex 32"
fi

echo ""
echo "Starting services..."
docker compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 5

# Check health
if curl -sf http://localhost:8000/healthz > /dev/null 2>&1; then
    echo "  Backend is healthy!"
else
    echo "  Backend is still starting... (check 'make logs')"
fi

echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "UAPK Gateway is running:"
echo "  Dashboard:    http://localhost:8000"
echo "  API Docs:     http://localhost:8000/docs"
echo "  PostgreSQL:   localhost:5432"
echo ""
echo "Useful commands:"
echo "  make logs     - Follow container logs"
echo "  make stop     - Stop services"
echo "  make test     - Run tests"
echo ""

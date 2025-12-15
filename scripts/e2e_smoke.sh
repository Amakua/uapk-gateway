#!/bin/bash
# End-to-end smoke test for UAPK Gateway
# Tests the full system including Docker deployment, migrations, and API workflows

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================"
echo "  UAPK Gateway - E2E Smoke Test"
echo "========================================"
echo ""
echo "Project: $PROJECT_ROOT"
echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ FAIL${NC}: Docker is not installed or not in PATH"
    echo ""
    echo "This E2E smoke test requires Docker to run."
    echo "Please install Docker and Docker Compose first:"
    echo "  https://docs.docker.com/get-docker/"
    echo ""
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ FAIL${NC}: Docker Compose is not available"
    echo ""
    echo "This E2E smoke test requires Docker Compose."
    echo "Please install Docker Compose:"
    echo "  https://docs.docker.com/compose/install/"
    echo ""
    exit 1
fi

echo "Docker: $(docker --version)"
echo "Docker Compose: $(docker compose version)"
echo ""

FAILED=0

# Function to run check
run_check() {
    local name="$1"
    local command="$2"

    echo "----------------------------------------"
    echo "CHECK: $name"
    echo "----------------------------------------"

    if eval "$command"; then
        echo -e "${GREEN}✓ PASS${NC}: $name"
        echo ""
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}: $name"
        echo ""
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up..."
    docker compose down -v 2>/dev/null || true
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Step 1: Validate compose configuration
run_check "Docker Compose config validation" "docker compose config > /dev/null"

# Step 2: Build and start services
echo "----------------------------------------"
echo "Starting Docker services..."
echo "----------------------------------------"
docker compose up -d --build
echo ""

# Step 3: Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10
echo ""

# Step 4: Check health endpoints
run_check "Health check (/healthz)" "curl -fsS http://localhost:8000/healthz"
run_check "Readiness check (/readyz)" "curl -fsS http://localhost:8000/readyz"

# Step 5: Run migrations
run_check "Database migrations" "docker compose exec -T backend alembic upgrade head"

# Step 6: Create bootstrap data
echo "----------------------------------------"
echo "Bootstrapping admin user and organization..."
echo "----------------------------------------"
if docker compose run --rm bootstrap; then
    echo -e "${GREEN}✓ PASS${NC}: Bootstrap"
    echo ""
else
    echo -e "${RED}✗ FAIL${NC}: Bootstrap"
    echo ""
    FAILED=$((FAILED + 1))
fi

# Step 7: Test API authentication
echo "----------------------------------------"
echo "Testing API authentication..."
echo "----------------------------------------"
TOKEN=$(curl -fsS -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "admin@example.com", "password": "changeme123"}' \
    | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")

if [ -n "$TOKEN" ]; then
    echo -e "${GREEN}✓ PASS${NC}: User authentication"
    echo "Token acquired: ${TOKEN:0:20}..."
    echo ""
else
    echo -e "${RED}✗ FAIL${NC}: User authentication"
    echo ""
    FAILED=$((FAILED + 1))
fi

# Step 8: Test authenticated endpoint
if [ -n "$TOKEN" ]; then
    run_check "Authenticated request (/api/v1/auth/me)" \
        "curl -fsS http://localhost:8000/api/v1/auth/me -H 'Authorization: Bearer $TOKEN'"
fi

# Step 9: Show logs on failure
if [ $FAILED -gt 0 ]; then
    echo ""
    echo "========================================"
    echo "  Container Logs (last 50 lines)"
    echo "========================================"
    echo ""
    docker compose logs --tail=50
fi

# Summary
echo "========================================"
echo "  E2E Smoke Test Summary"
echo "========================================"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All E2E checks passed!${NC}"
    echo ""
    echo "The UAPK Gateway is fully functional."
    echo ""
    exit 0
else
    echo -e "${RED}Failed checks: $FAILED${NC}"
    echo ""
    echo "To debug:"
    echo "  docker compose logs backend"
    echo "  docker compose logs postgres"
    echo ""
    exit 1
fi

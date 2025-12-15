#!/bin/bash
# Self-check script for UAPK Gateway
# Runs fast verification checks without requiring Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "========================================"
echo "  UAPK Gateway - Self Check"
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

# Check 1: Environment file
run_check "Environment file exists" "test -f .env || test -f .env.example"

# Check 2: Code formatting
run_check "Code formatting (ruff format --check)" "ruff format --check backend/"

# Check 3: Linting
run_check "Linting (ruff check)" "ruff check backend/"

# Check 4: Type checking
run_check "Type checking (mypy)" "cd backend && mypy app/"

# Check 5: Unit tests
run_check "Unit tests (pytest)" "cd backend && pytest -v"

# Check 6: Documentation build
run_check "Documentation build" "mkdocs build --strict"

echo "========================================"
echo "  Self Check Summary"
echo "========================================"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}Failed checks: $FAILED${NC}"
    echo ""
    echo "To fix issues:"
    echo "  - Format:    make format"
    echo "  - Lint:      make lint"
    echo "  - Typecheck: make typecheck"
    echo "  - Test:      make test-local"
    echo "  - Docs:      make docs-build"
    echo ""
    exit 1
fi

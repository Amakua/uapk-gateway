.PHONY: help dev stop logs build rebuild test lint format typecheck clean docs docs-build docs-deploy install migrate bootstrap demo demo-list

# Default target
help:
	@echo "UAPK Gateway - Development Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev          Start development environment (docker compose up)"
	@echo "  make stop         Stop development environment"
	@echo "  make logs         Follow container logs"
	@echo "  make rebuild      Rebuild and restart containers"
	@echo ""
	@echo "Database:"
	@echo "  make migrate      Run database migrations"
	@echo "  make bootstrap    Create initial admin user and organization"
	@echo "  make db-shell     Open PostgreSQL shell"
	@echo "  make db-reset     Reset database (destroys all data)"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run pytest"
	@echo "  make test-cov     Run pytest with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         Run ruff linter"
	@echo "  make format       Format code with ruff"
	@echo "  make typecheck    Run mypy type checker"
	@echo "  make check        Run all checks (lint, typecheck, test)"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs         Serve documentation locally (port 8080)"
	@echo "  make docs-build   Build documentation for production"
	@echo "  make docs-deploy  Deploy documentation to GitHub Pages"
	@echo ""
	@echo "Demo:"
	@echo "  make demo         Load 47er example manifests and print curl commands"
	@echo "  make demo-list    List available 47er templates"
	@echo ""
	@echo "Setup:"
	@echo "  make install      Install dependencies locally"
	@echo "  make clean        Clean up generated files"

# Development
dev:
	docker compose up -d
	@echo ""
	@echo "UAPK Gateway is starting..."
	@echo "  Dashboard: http://localhost:8000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run 'make migrate' to set up the database"
	@echo "  2. Run 'make bootstrap' to create admin user"
	@echo "  3. Run 'make logs' to follow container logs"

stop:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d

# Database
migrate:
	docker compose run --rm migrate
	@echo ""
	@echo "Database migrations complete!"

bootstrap:
	docker compose run --rm bootstrap
	@echo ""
	@echo "Bootstrap complete! You can now login with the admin credentials."

db-shell:
	docker compose exec postgres psql -U uapk -d uapk

db-reset:
	docker compose down -v
	docker compose up -d postgres
	@echo "Waiting for postgres to be ready..."
	@sleep 5
	docker compose up -d
	@echo ""
	@echo "Database reset. Run 'make migrate && make bootstrap' to set up again."

# Testing
test:
	docker compose exec backend pytest

test-cov:
	docker compose exec backend pytest --cov=app --cov-report=html --cov-report=term

test-local:
	cd backend && pytest

# Code Quality
lint:
	ruff check backend/

format:
	ruff format backend/
	ruff check --fix backend/

typecheck:
	cd backend && mypy app/

check: lint typecheck test-local

# Documentation
docs:
	mkdocs serve --dev-addr 0.0.0.0:8080

docs-build:
	mkdocs build --strict

docs-deploy:
	mkdocs gh-deploy --force

# Setup
install:
	pip install -e ".[dev,docs]"

install-hooks:
	pre-commit install

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name site -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

# Production
prod-up:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Demo - 47ers Library
demo-list:
	@python3 scripts/load_example_manifests.py --list

demo:
	@echo ""
	@echo "========================================"
	@echo "  UAPK Gateway - 47ers Demo Mode"
	@echo "========================================"
	@echo ""
	@echo "This will load 47er example manifests into the gateway."
	@echo ""
	@echo "Prerequisites:"
	@echo "  1. Gateway running (make dev)"
	@echo "  2. Database migrated (make migrate)"
	@echo "  3. Bootstrap complete (make bootstrap)"
	@echo ""
	@if [ -z "$$ORG_ID" ]; then \
		echo "Set environment variables:"; \
		echo "  export ORG_ID=<your-org-id>"; \
		echo "  export TOKEN=<your-bearer-token>"; \
		echo ""; \
		echo "Then run: make demo"; \
		echo ""; \
		echo "Or run with dry-run mode to preview:"; \
		echo "  python3 scripts/load_example_manifests.py --all --dry-run"; \
		exit 1; \
	fi
	@echo "Loading 47er templates..."
	@python3 scripts/load_example_manifests.py \
		--all \
		--demo \
		--org-id $$ORG_ID \
		--token $$TOKEN \
		--api-url $${API_URL:-http://localhost:8000}
	@echo ""
	@echo "========================================"
	@echo "  Demo manifests loaded!"
	@echo "========================================"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Visit http://localhost:8000/ui to see manifests in the dashboard"
	@echo "  2. Try executing actions with the curl commands above"
	@echo "  3. Check pending approvals for escalated actions"
	@echo "  4. Verify audit logs with chain verification"
	@echo ""

demo-dry-run:
	@python3 scripts/load_example_manifests.py --all --dry-run --demo

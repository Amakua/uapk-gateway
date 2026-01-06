# Contributing

How to contribute to UAPK Gateway.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Set up development environment

```bash
git clone https://github.com/YOUR_USERNAME/uapk-gateway.git
cd uapk-gateway
make dev
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code
- Add tests
- Update documentation

### 3. Test

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run linting
make lint

# Run type checking
make typecheck
```

### 4. Commit

Follow conventional commits:

```bash
git commit -m "feat: add capability token validation"
git commit -m "fix: handle null manifest fields"
git commit -m "docs: update API documentation"
```

### 5. Submit PR

- Push your branch
- Open a pull request
- Fill out the PR template
- Wait for review

## Code Style

- **Python**: Follow PEP 8, enforced by ruff
- **Types**: Use type hints everywhere
- **Docs**: Docstrings for public functions
- **Tests**: Required for new features

## Project Structure

```
backend/
├── app/
│   ├── api/          # API endpoints
│   ├── core/         # Config, logging
│   ├── models/       # Database models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── ui/           # Operator dashboard
└── tests/            # Test suite
```

## Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_health.py

# With coverage
pytest --cov=app --cov-report=html
```

## Documentation

Documentation uses MkDocs:

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Serve locally
mkdocs serve

# Build
mkdocs build
```

## Questions?

- Open a GitHub issue
- Check existing issues first
- Be specific and include context

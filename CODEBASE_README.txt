UAPK GATEWAY - CODEBASE PACKAGE
================================

This archive contains the complete UAPK Gateway codebase, ready for review and development.

## What's Included

- Full source code (Python backend, FastAPI)
- Complete documentation website (MkDocs Material)
- Business model documents (pilot SOW, enterprise pitch, security policy)
- Infrastructure configuration (Docker Compose, GitHub Actions)
- Example manifests ("47ers" - pre-built templates)
- Database schema and migrations (Alembic)

## What's Excluded

- .git directory (version control history)
- Virtual environments (venv/, env/)
- Build artifacts (site/, __pycache__, dist/)
- Environment files (.env - contains secrets)
- Database files (*.db, postgres_data/)
- IDE configs (.vscode/, .idea/)
- Cache directories (.mypy_cache/, .ruff_cache/)

## Quick Start

1. Extract this archive
2. Copy .env.example to .env and configure
3. Run: docker compose up -d
4. Run: make migrate && make bootstrap
5. Access: http://localhost:8000

## Documentation Website

The documentation is built with MkDocs Material and deploys to:
- Production: https://uapk.info
- Local build: mkdocs serve (requires: pip install mkdocs mkdocs-material)

## Project Structure

uapk-gateway/
├── backend/              # FastAPI application
│   ├── app/             # Main application code
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Core business logic
│   │   ├── models/      # Database models
│   │   └── schemas/     # Pydantic schemas
│   ├── alembic/         # Database migrations
│   ├── scripts/         # Utility scripts
│   └── tests/           # Test suite
├── docs/                # MkDocs documentation
│   ├── business/        # Business model docs (pricing, pilot, pitch)
│   ├── concepts/        # Architecture concepts
│   ├── api/             # API reference
│   ├── operator/        # Operator guides
│   ├── security/        # Security documentation
│   └── deployment/      # Deployment guides
├── examples/            # Example configurations
│   └── 47ers/           # Pre-built manifest templates
├── deploy/              # Deployment configurations
├── schemas/             # JSON schemas for manifests
├── .github/workflows/   # CI/CD workflows
├── docker-compose.yml   # Development environment
├── docker-compose.prod.yml  # Production environment
├── mkdocs.yml           # Documentation configuration
├── pyproject.toml       # Python project configuration
└── Makefile             # Development commands

## Key Technologies

- **Backend:** Python 3.12, FastAPI, PostgreSQL 16, SQLAlchemy
- **Auth:** JWT (humans), API keys (machines), Ed25519 capability tokens
- **Frontend:** Jinja2 templates + HTMX (lightweight)
- **Docs:** MkDocs Material (deployed to GitHub Pages)
- **Infrastructure:** Docker Compose, Caddy (reverse proxy)
- **CI/CD:** GitHub Actions

## Business Model (Current Vision)

- **Open Source:** Apache-2.0 license, free self-hosting
- **Pilot Program:** $15K-$25K fixed-fee (2-4 weeks)
- **Enterprise Support:** $3K-$10K/month (custom connectors, SLA)
- **Target Audience:** Law firms, banks, fintechs, compliance teams

## Website Updates (Recent)

The website has been transformed from a SaaS-focused model to a pilot-first approach:
- Homepage: "Agent firewall + black box recorder" positioning
- Pricing: Open-source + pilots (no SaaS tiers)
- New pages: Future-proof architecture, security policy, enterprise pitch
- 47ers library prominently featured
- All contact consolidated to: mail@uapk.info

## GitHub Repository

https://github.com/Amakua/uapk-core

## Contact

- Email: mail@uapk.info
- Security: mail@uapk.info (include "SECURITY" in subject)

## Archive Information

Created: $(date)
Archive size: $(ls -lh /home/dsanker/uapk-gateway-codebase.tar.gz | awk '{print $5}')
File count: 266 files
Compression: gzip (tar.gz)

---

Ready for review and enhancement! 🚀

# Technical Decisions

Record of key technical decisions for UAPK Gateway.

## Decision Log

### 2024-01: Single VM Architecture

**Context**: Need to deploy UAPK Gateway for small-to-medium organizations.

**Decision**: Deploy everything on a single VM using Docker Compose.

**Rationale**:
- Simplicity over scalability for v0.x
- Easier to operate and debug
- Lower infrastructure costs
- Can migrate to k8s later if needed

**Consequences**:
- Limited horizontal scaling
- Single point of failure
- Simpler deployment and operations

---

### 2024-01: Python + FastAPI

**Context**: Choose backend language and framework.

**Decision**: Python 3.12 with FastAPI.

**Rationale**:
- FastAPI is fast, modern, and well-documented
- Automatic OpenAPI spec generation
- Native async support
- Strong typing with Pydantic
- Large ecosystem for AI/ML integration
- Team familiarity

**Alternatives Considered**:
- Go + Chi: Faster, but less AI ecosystem
- Rust + Axum: Fastest, but higher learning curve
- Node + Fastify: Good, but Python has better AI libs

---

### 2024-01: PostgreSQL

**Context**: Choose primary database.

**Decision**: PostgreSQL 16.

**Rationale**:
- Battle-tested and reliable
- Excellent JSON support for flexible schemas
- Strong consistency guarantees
- Rich extension ecosystem (uuid, pgcrypto)
- Familiar to most developers

**Alternatives Considered**:
- SQLite: Too limited for production
- MySQL: PostgreSQL has better JSON support
- MongoDB: Not needed, prefer SQL

---

### 2024-01: Server-Rendered UI

**Context**: How to build the operator dashboard.

**Decision**: FastAPI + Jinja2 + HTMX (no separate frontend).

**Rationale**:
- Simpler architecture (no Node.js)
- Faster initial page loads
- Works without JavaScript
- HTMX provides interactivity where needed
- Easier to maintain

**Alternatives Considered**:
- React SPA: More complex, separate build
- Vue.js: Same issues as React
- Svelte: Interesting, but adds complexity

---

### 2024-01: Hatchling for Packaging

**Context**: Choose Python build system.

**Decision**: Use hatchling (pyproject.toml only).

**Rationale**:
- Modern PEP 517/518 compliant
- Single pyproject.toml file
- Faster than setuptools
- Good dependency management

**Alternatives Considered**:
- Poetry: More features, but more complex
- setuptools: Older, requires setup.py

---

### 2024-01: Structlog for Logging

**Context**: Choose logging library.

**Decision**: structlog with JSON output.

**Rationale**:
- Structured logs are easier to parse
- Good integration with standard logging
- Context propagation support
- JSON output for log aggregation

---

### 2024-01: HMAC for Audit Signatures

**Context**: How to sign InteractionRecords.

**Decision**: HMAC-SHA256 using server secret.

**Rationale**:
- Simple and fast
- Sufficient for tamper detection
- Can upgrade to asymmetric signing later
- No PKI infrastructure needed

**Future Consideration**:
- Ed25519 signatures for non-repudiation
- Hardware security modules for key storage

---

## Pending Decisions

### TBD: Message Queue

For async processing and webhooks. Options:
- Redis Streams
- PostgreSQL LISTEN/NOTIFY
- RabbitMQ
- No queue (sync only)

### TBD: Caching Strategy

For policy evaluation and token validation. Options:
- In-memory (per-process)
- Redis
- No caching

### TBD: Multi-tenancy Model

How to isolate organizations. Options:
- Schema per tenant
- Row-level security
- Separate databases

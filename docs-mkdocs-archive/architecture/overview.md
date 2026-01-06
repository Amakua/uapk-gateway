# Architecture Overview

UAPK Gateway is designed as a single-VM deployment using Docker Compose.

## System Architecture

```mermaid
graph TB
    subgraph "External"
        A[AI Agents]
        H[Human Operators]
    end

    subgraph "UAPK Gateway VM"
        subgraph "Docker Compose"
            C[Caddy<br/>Reverse Proxy]
            B[FastAPI Backend]
            P[(PostgreSQL)]
        end
    end

    subgraph "External Tools"
        T1[Email API]
        T2[Storage API]
        T3[Custom Tools]
    end

    A -->|Action Requests| C
    H -->|Dashboard| C
    C --> B
    B --> P
    B -->|Approved Actions| T1
    B -->|Approved Actions| T2
    B -->|Approved Actions| T3
```

## Component Overview

### Backend (FastAPI)

The core application handling:

- **API Layer**: RESTful endpoints for agents and operators
- **Policy Engine**: Evaluates action requests against policies
- **Audit Logger**: Creates tamper-evident InteractionRecords
- **Operator UI**: Server-rendered dashboard with HTMX

### Database (PostgreSQL)

Stores:

- Organizations and teams
- Agent registrations and manifests
- Policies and capability tokens
- InteractionRecords (audit log)

### Reverse Proxy (Caddy)

Production deployment includes Caddy for:

- Automatic TLS certificates
- Request routing
- Security headers
- Rate limiting

## Request Flow

```mermaid
sequenceDiagram
    participant Agent
    participant API
    participant Auth
    participant Policy
    participant Executor
    participant AuditLog
    participant DB

    Agent->>API: POST /v1/actions
    API->>Auth: Validate token
    Auth->>DB: Check capability token
    Auth-->>API: Token valid

    API->>Policy: Evaluate request
    Policy->>DB: Load policies
    Policy-->>API: Decision + reasons

    alt Approved
        API->>Executor: Execute action
        Executor-->>API: Result
    end

    API->>AuditLog: Create InteractionRecord
    AuditLog->>DB: Store signed record

    API-->>Agent: Response
```

## Directory Structure

```
uapk-gateway/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/       # API routes
│   │   ├── core/      # Configuration, logging
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   └── ui/        # Operator dashboard
│   └── tests/
├── deploy/            # Deployment configs
│   ├── caddy/
│   ├── postgres/
│   └── systemd/
├── docs/              # MkDocs documentation
├── schemas/           # JSON schemas
├── examples/          # Example manifests
└── scripts/           # Helper scripts
```

## Design Principles

1. **Single VM**: Everything runs on one machine via Docker Compose
2. **Boring Tech**: PostgreSQL, FastAPI, standard libraries
3. **Typed Everything**: Python type hints, Pydantic validation
4. **Audit First**: Every action creates a signed log entry
5. **Operator Control**: Humans can always intervene

---
title: Core Concepts
description: Understanding UAPK Gateway architecture and concepts
---

# Core Concepts

UAPK Gateway provides a policy enforcement layer between AI agents and the tools they use. This section explains the core concepts.

## Architecture Overview

```mermaid
flowchart TB
    subgraph Agents
        A1[Customer Support Bot]
        A2[Deployment Bot]
        A3[Research Agent]
    end

    subgraph UAPK Gateway
        GW[Gateway API]
        PE[Policy Engine]
        AL[Audit Logger]
        AW[Approval Workflow]
    end

    subgraph Tools
        T1[Email API]
        T2[CRM]
        T3[GitHub]
        T4[Kubernetes]
    end

    subgraph Storage
        DB[(PostgreSQL)]
    end

    A1 --> GW
    A2 --> GW
    A3 --> GW

    GW --> PE
    PE --> AL
    PE --> AW
    AL --> DB
    AW --> DB

    GW --> T1
    GW --> T2
    GW --> T3
    GW --> T4
```

## Request Flow

Every agent action request flows through the gateway:

```mermaid
sequenceDiagram
    participant Agent
    participant Gateway
    participant Policy Engine
    participant Connector
    participant Audit

    Agent->>Gateway: Action Request
    Gateway->>Policy Engine: Evaluate

    Note over Policy Engine: Check manifest
    Note over Policy Engine: Validate capability token
    Note over Policy Engine: Check policies
    Note over Policy Engine: Check budgets

    alt ALLOW
        Policy Engine-->>Gateway: ALLOW
        Gateway->>Connector: Execute
        Connector-->>Gateway: Result
        Gateway->>Audit: Log (hash + sign)
        Gateway-->>Agent: Success
    else DENY
        Policy Engine-->>Gateway: DENY + reasons
        Gateway->>Audit: Log violation
        Gateway-->>Agent: Policy violation
    else ESCALATE
        Policy Engine-->>Gateway: ESCALATE
        Gateway->>Audit: Create approval
        Gateway-->>Agent: Pending approval
    end
```

## Key Concepts

| Concept | Description | Learn More |
|---------|-------------|------------|
| **UAPK Manifest** | JSON document declaring agent identity, capabilities, and constraints | [Manifest](manifest.md) |
| **Capability Token** | Ed25519-signed JWT granting specific permissions | [Capabilities](capabilities.md) |
| **Policy Decision** | ALLOW, DENY, or ESCALATE based on evaluation | [Decisions](decisions.md) |
| **Approval Workflow** | Human review for escalated actions | [Approvals](approvals.md) |
| **Audit Log** | Hash-chained, signed InteractionRecords | [Logs](logs.md) |

## Multi-Tenancy

UAPK Gateway supports multiple organizations with isolated data:

```mermaid
flowchart TB
    subgraph "Organization: Acme Corp"
        O1_M1[Support Bot Manifest]
        O1_M2[Deploy Bot Manifest]
        O1_P[Policies]
        O1_L[Audit Logs]
    end

    subgraph "Organization: Globex"
        O2_M1[Sales Bot Manifest]
        O2_P[Policies]
        O2_L[Audit Logs]
    end

    GW[UAPK Gateway]
    GW --> O1_M1
    GW --> O1_M2
    GW --> O2_M1
```

Each organization has:

- Independent manifests and agents
- Separate policies and approval workflows
- Isolated audit logs
- Distinct API keys and users

## Security Model

UAPK Gateway implements defense-in-depth:

1. **Authentication**: JWT tokens for users, API keys for agents
2. **Authorization**: RBAC for operators, capability tokens for agents
3. **Policy Enforcement**: Rules evaluated at runtime
4. **Audit Trail**: Tamper-evident, cryptographically signed logs
5. **Key Management**: Ed25519 keys for signing tokens and records

See [Security](../security/index.md) for the full threat model.

## Next Steps

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
### :material-file-document: [UAPK Manifest](manifest.md)
Learn how to declare agent identity and capabilities.
</div>

<div class="feature-card" markdown>
### :material-key: [Capability Tokens](capabilities.md)
Understand fine-grained, time-limited permissions.
</div>

<div class="feature-card" markdown>
### :material-scale-balance: [Policy Decisions](decisions.md)
How the policy engine evaluates requests.
</div>

<div class="feature-card" markdown>
### :material-account-check: [Approvals](approvals.md)
Configure human-in-the-loop workflows.
</div>

</div>

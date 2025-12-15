---
title: Security
description: Security architecture and practices for UAPK Gateway
---

# Security

UAPK Gateway is designed with security as a core principle, providing defense-in-depth for AI agent operations.

## Security Model

```mermaid
flowchart TB
    subgraph "Defense in Depth"
        L1[Layer 1: Authentication]
        L2[Layer 2: Authorization]
        L3[Layer 3: Policy Enforcement]
        L4[Layer 4: Audit & Verification]
    end

    Agent[Agent] --> L1
    L1 --> L2
    L2 --> L3
    L3 --> L4
    L4 --> Action[Action Execution]
```

## Security Principles

### 1. Zero Trust

- Every request is authenticated and authorized
- No implicit trust based on network location
- Continuous validation of credentials and capabilities

### 2. Least Privilege

- Agents only get the capabilities they declare
- Capability tokens can further restrict permissions
- Time-limited access by default

### 3. Defense in Depth

- Multiple layers of security controls
- No single point of failure
- Independent verification at each layer

### 4. Tamper Evidence

- Cryptographically signed audit logs
- Hash-chained records
- Offline verification capability

## Security Topics

<div class="grid cards" markdown>

-   :material-shield-alert: **Threat Model**

    ---

    Understand the threats UAPK Gateway protects against

    [:octicons-arrow-right-24: Threat Model](threat-model.md)

-   :material-database-lock: **Data Handling**

    ---

    How data is stored, transmitted, and protected

    [:octicons-arrow-right-24: Data Handling](data-handling.md)

-   :material-key: **Key Management**

    ---

    Managing Ed25519 signing keys securely

    [:octicons-arrow-right-24: Key Management](key-management.md)

</div>

## Security Features

| Feature | Description |
|---------|-------------|
| **Ed25519 Signatures** | Cryptographic signing of all audit records |
| **Hash Chaining** | Tamper-evident log chain |
| **JWT Capability Tokens** | Fine-grained, time-limited permissions |
| **Policy Enforcement** | Configurable allow/deny/escalate rules |
| **Human-in-the-Loop** | Approval workflow for sensitive actions |
| **Audit Trail** | Complete history of all decisions |

## Quick Security Checklist

- [ ] Use HTTPS in production
- [ ] Rotate API keys regularly
- [ ] Set short expiry for capability tokens
- [ ] Enable approval for sensitive actions
- [ ] Verify log chain integrity daily
- [ ] Backup signing keys securely
- [ ] Monitor for unusual activity
- [ ] Review denied actions for patterns

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** open a public GitHub issue
2. Email security@uapk.dev with details
3. Include steps to reproduce if possible
4. We'll respond within 48 hours

## Related

- [Threat Model](threat-model.md) - Detailed threat analysis
- [Data Handling](data-handling.md) - Data protection
- [Key Management](key-management.md) - Key security

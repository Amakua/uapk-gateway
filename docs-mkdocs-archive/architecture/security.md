# Security Model

How UAPK Gateway provides security for AI agent operations.

## Authentication

### Human Operators

- JWT tokens issued after login
- Configurable expiration
- Role-based access control (future)

### AI Agents

- API keys for identification
- Capability tokens for authorization
- Tokens are scoped and time-limited

## Authorization

### Capability-Based Security

Agents can only perform actions explicitly granted:

1. Agent registers with a Manifest
2. Operator reviews and approves capabilities
3. Gateway issues Capability Token
4. Every request is checked against token

### Policy Enforcement

Multiple layers of policy checks:

```
Request → Auth → Capability Check → Policy Engine → Execute
                                          ↓
                                    Rate Limits
                                    Budget Limits
                                    Time Restrictions
                                    Custom Rules
```

## Audit Trail

### Tamper-Evident Logging

Every InteractionRecord includes:

- **Signature**: HMAC of record contents
- **Chain Hash**: Hash including previous record

This creates a blockchain-like chain where any modification is detectable.

### What's Logged

- All action requests (approved or denied)
- Policy evaluation results
- Execution results or errors
- Timestamps and agent identification

## Data Protection

### Secrets Management

- Secrets via environment variables
- Never logged or exposed in API
- Database credentials isolated

### Network Security

- TLS everywhere in production
- Internal services on Docker network
- No direct database access from outside

## Threat Model

### Threats Addressed

| Threat | Mitigation |
|--------|------------|
| Agent exceeds scope | Capability tokens + policies |
| Unauthorized action | Multi-layer auth checks |
| Audit log tampering | Signed, chained records |
| Credential theft | Short-lived tokens, revocation |
| Resource exhaustion | Rate limits, budgets |

### Out of Scope (v0.1)

- Multi-region deployment
- Hardware security modules
- Zero-knowledge proofs

## Best Practices

### For Operators

1. Use strong, unique SECRET_KEY
2. Review agent manifests carefully
3. Start with restrictive policies
4. Monitor audit logs regularly
5. Rotate capability tokens

### For Agent Developers

1. Request minimum necessary capabilities
2. Include meaningful context in requests
3. Handle policy denials gracefully
4. Don't store capability tokens long-term

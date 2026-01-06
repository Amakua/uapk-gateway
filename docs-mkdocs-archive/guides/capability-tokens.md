# Capability Tokens

Capability tokens are Ed25519-signed JWTs that grant specific permissions to AI agents. They provide fine-grained, time-limited authorization that works in conjunction with UAPK manifests.

## Overview

When an agent makes a request to the gateway, permissions are determined by the **intersection** of:
1. The UAPK manifest constraints
2. The capability token constraints (if provided)

This means a capability token can only restrict permissions further, never expand beyond what the manifest allows.

## Token Structure

Capability tokens are JWTs with the following claims:

```json
{
  "iss": "gateway",           // Issuer ID
  "sub": "agent-123",         // Agent ID
  "org_id": "uuid",           // Organization ID
  "uapk_id": "my-agent",      // UAPK manifest ID
  "allowed_action_types": ["payment", "data_access"],
  "allowed_tools": ["stripe_transfer", "email_send"],
  "constraints": {
    "amount_max": 1000.0,
    "jurisdictions": ["US", "CA"],
    "counterparty_allowlist": ["vendor-1", "vendor-2"]
  },
  "delegation_depth": 0,
  "iat": 1702500000,          // Issued at (Unix timestamp)
  "exp": 1702503600,          // Expires at (Unix timestamp)
  "jti": "cap-abc123"         // Unique token ID
}
```

## Token Claims

| Claim | Description |
|-------|-------------|
| `iss` | Issuer ID - either "gateway" or a registered issuer |
| `sub` | Agent ID the token is issued to |
| `org_id` | Organization the token belongs to |
| `uapk_id` | UAPK manifest the token is bound to |
| `allowed_action_types` | Action types the agent can perform |
| `allowed_tools` | Specific tools the agent can use |
| `constraints` | Additional constraints (see below) |
| `delegation_depth` | How many times the token can be delegated (0 = no delegation) |
| `iat` | Issued at timestamp |
| `exp` | Expiration timestamp |
| `jti` | Unique token identifier |

## Constraints

Constraints embedded in the token limit what the agent can do:

| Constraint | Description |
|------------|-------------|
| `amount_max` | Maximum amount for financial operations |
| `jurisdictions` | Allowed jurisdiction codes (ISO country codes) |
| `counterparty_allowlist` | Only these counterparties are allowed |
| `counterparty_denylist` | These counterparties are blocked |
| `expires_at` | Hard expiration (separate from token expiry) |

## Issuing Tokens

### Via API

```bash
# Issue a capability token
curl -X POST /v1/capabilities/issue \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "my-agent-instance",
    "uapk_id": "my-agent",
    "allowed_action_types": ["payment"],
    "allowed_tools": ["stripe_transfer"],
    "constraints": {
      "amount_max": 500,
      "jurisdictions": ["US"]
    },
    "expires_in_seconds": 3600
  }'
```

Response:
```json
{
  "token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...",
  "token_id": "cap-abc123def456",
  "issuer_id": "gateway",
  "agent_id": "my-agent-instance",
  "uapk_id": "my-agent",
  "org_id": "uuid",
  "issued_at": "2024-12-14T10:00:00Z",
  "expires_at": "2024-12-14T11:00:00Z",
  "allowed_action_types": ["payment"],
  "allowed_tools": ["stripe_transfer"],
  "constraints": {
    "amount_max": 500,
    "jurisdictions": ["US"]
  }
}
```

## Using Tokens

Include the token in gateway requests:

```bash
curl -X POST /v1/gateway/execute \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "my-agent",
    "agent_id": "my-agent-instance",
    "capability_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...",
    "action": {
      "type": "payment",
      "tool": "stripe_transfer",
      "params": {
        "amount": 100,
        "currency": "USD",
        "recipient": "vendor-123"
      }
    }
  }'
```

## Registering External Issuers

Organizations can register external systems as capability issuers:

```bash
# Register an external issuer
curl -X POST /v1/capabilities/issuers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "issuer_id": "external-system-1",
    "name": "External Authorization System",
    "public_key": "base64-encoded-ed25519-public-key",
    "description": "Our external auth system for agents"
  }'
```

Tokens signed by registered issuers are verified using their public keys.

### Getting the Gateway Public Key

```bash
# Get gateway's public key (for external verification)
curl /v1/capabilities/gateway-key
```

```json
{
  "issuer_id": "gateway",
  "public_key": "base64-encoded-ed25519-public-key",
  "algorithm": "EdDSA"
}
```

## Revoking Issuers

If an external issuer's key is compromised, revoke it immediately:

```bash
curl -X POST /v1/capabilities/issuers/external-system-1/revoke \
  -H "Authorization: Bearer $TOKEN"
```

Tokens from revoked issuers will no longer be accepted.

## Security Considerations

### Token Lifetime

- Use short-lived tokens (1-8 hours for interactive use)
- Use very short tokens (1-5 minutes) for one-time operations
- Override tokens from approvals expire in 5 minutes by default

### Principle of Least Privilege

Issue tokens with the minimum permissions needed:

```json
// Good: Specific permissions
{
  "allowed_action_types": ["data_access"],
  "allowed_tools": ["read_customer_profile"],
  "constraints": {
    "counterparty_allowlist": ["customer-123"]
  }
}

// Bad: Overly broad permissions
{
  "allowed_action_types": [],  // Empty = all types
  "allowed_tools": []          // Empty = all tools
}
```

### Key Rotation

- Rotate the gateway keypair periodically
- Keep old public keys available briefly for token verification during transition
- Register new keys with any external systems that verify gateway tokens

## Error Handling

Common token-related errors:

| Error Code | Description |
|------------|-------------|
| `capability_token_invalid` | Token signature verification failed |
| `capability_token_expired` | Token has expired |
| `token_issuer_revoked` | Issuer has been revoked |
| `token_agent_mismatch` | Token's sub doesn't match agent_id |
| `token_org_mismatch` | Token's org_id doesn't match request |
| `token_uapk_mismatch` | Token's uapk_id doesn't match request |
| `token_action_type_not_allowed` | Action type not in token's allowed list |
| `token_tool_not_allowed` | Tool not in token's allowed list |
| `token_amount_exceeds_cap` | Amount exceeds token's amount_max |
| `token_jurisdiction_not_allowed` | Jurisdiction not in token's allowed list |
| `token_counterparty_not_allowed` | Counterparty blocked by token |

## Next Steps

- [Approval Workflow](approvals.md) - Learn about human-in-the-loop approvals
- [Policies](policies.md) - Configure organization policies
- [API Reference](../api/endpoints.md) - Full API documentation

---
title: Security Policy
description: Vulnerability reporting and security practices
---

# Security Policy

UAPK Gateway is designed for high-stakes environments. We take security seriously.

---

## Reporting a Vulnerability

**DO NOT** open a public GitHub issue for security vulnerabilities.

### How to Report

<div class="grid cards" markdown>

-   :material-shield-alert: **GitHub Security Advisories** (preferred)

    ---

    Navigate to [https://github.com/UAPK/gateway/security/advisories](https://github.com/UAPK/gateway/security/advisories) and click "Report a vulnerability"

-   :material-email: **Email**

    ---

    Email: [mail@uapk.info](mailto:mail@uapk.info) with "SECURITY" in the subject line. PGP key available on request.

</div>

### What to Include

- Description of the vulnerability
- Steps to reproduce the issue
- Affected versions
- Potential impact assessment
- Suggested fix (if available)

### Response Timeline

- **Initial response:** Within 48 hours
- **Triage and assessment:** Within 5 business days
- **Fix timeline:** Depends on severity (critical issues prioritized)
- **Disclosure:** Coordinated with reporter after fix is available

### Disclosure Policy

We follow **coordinated disclosure**:

1. You report the issue privately
2. We confirm and develop a fix
3. We release the fix and publish a security advisory
4. You receive credit (if desired)

---

## Security Features

UAPK Gateway is designed for regulated environments:

### Authentication & Authorization

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
#### JWT Tokens
For human users (HS256, configurable expiration)
</div>

<div class="feature-card" markdown>
#### API Keys
For machine clients (hashed with bcrypt, one-way)
</div>

<div class="feature-card" markdown>
#### Capability Tokens
For scoped delegation (signed JWTs with Ed25519)
</div>

<div class="feature-card" markdown>
#### RBAC
Role-based access control for organizations
</div>

</div>

---

### Data Protection

- **Secrets encryption:** Fernet (AES-128) for stored secrets
- **Password hashing:** bcrypt with configurable work factor
- **API key hashing:** One-way hash, full key shown only at creation
- **Environment-based secrets:** All sensitive config in `.env` (gitignored)

---

### Audit & Integrity

- **Tamper-evident logs:** Hash-chained interaction records
- **Gateway signatures:** Ed25519 signatures on log entries
- **Chain verification:** Standalone verification scripts ([verify_log_chain.py](https://github.com/UAPK/gateway/blob/main/backend/scripts/verify_log_chain.py))
- **Immutable records:** No deletion, only archival

---

### Network Security

- **CORS controls:** Configurable allowed origins
- **Connector allowlists:** Restrict webhook/HTTP destinations
- **TLS/HTTPS:** Required in production (via Caddy or reverse proxy)
- **Rate limiting:** Planned (coming soon)

---

### Operational Security

- **Safe defaults:** Mock AI provider, sensitive data disabled
- **Input validation:** Pydantic schemas for all inputs
- **SQL injection protection:** SQLAlchemy ORM (parameterized queries)
- **Security headers:** Coming soon

---

## Security Best Practices

### For Operators

!!! warning "Change default credentials immediately"
    After bootstrap, change the admin password:
    ```bash
    curl -X POST http://localhost:8000/api/v1/auth/change-password \
      -H "Authorization: Bearer $TOKEN" \
      -d '{"old_password": "changeme123", "new_password": "..."}'
    ```

**Critical Actions:**

1. **Use strong SECRET_KEY**
   ```bash
   openssl rand -hex 32
   # Update .env with the generated key
   ```

2. **Rotate API keys regularly**
   - Revoke old keys: `POST /api/v1/api-keys/{id}/revoke`
   - Create new keys with minimal scopes

3. **Enable HTTPS in production**
   - Use Caddy (included in `docker-compose.prod.yml`)
   - Or use a reverse proxy (nginx, Traefik, etc.)

4. **Backup encryption keys**
   - `SECRET_KEY` (JWT signing)
   - `GATEWAY_FERNET_KEY` (secrets encryption)
   - Store securely (vault, KMS, encrypted backup)

5. **Monitor logs**
   - Review interaction records regularly
   - Export audit bundles for compliance
   - Verify chain integrity: `python scripts/verify_log_chain.py`

6. **Limit connector destinations**
   ```env
   # In .env
   GATEWAY_ALLOWED_WEBHOOK_DOMAINS=["example.com", "api.trusted.com"]
   ```

7. **Review manifests before activation**
   - Validate manifest schemas
   - Audit action allowlists
   - Verify budget limits

---

### For Developers

1. **Never commit secrets**
   - `.env` is in `.gitignore` - keep it there
   - Use `.env.example` for templates

2. **Run security checks**
   ```bash
   make typecheck  # Type safety
   make lint       # Security linters
   make test       # Security test cases
   ```

3. **Review dependencies**
   ```bash
   pip install safety
   safety check --json
   ```

4. **Follow secure coding practices**
   - Validate all inputs (use Pydantic)
   - Avoid eval/exec
   - Use parameterized queries (SQLAlchemy)
   - No shell injection (careful with subprocess)

5. **Test authentication/authorization**
   - Write tests for permission checks
   - Verify API key scoping
   - Test capability token validation

---

## Threat Model

See [Threat Model](threat-model.md) for detailed threat analysis.

### In Scope

- API authentication bypass
- Authorization violations (privilege escalation)
- SQL injection
- XSS in operator UI
- Log tampering or deletion
- Secret exposure
- Denial of service (application-level)

### Out of Scope (for vulnerability reports)

- Physical access to servers
- Social engineering
- DDoS (network-level)
- Vulnerabilities in third-party dependencies (report to upstream)
- Theoretical attacks requiring impractical resources

---

## Compliance Status

| Standard | Status | Notes |
|----------|--------|-------|
| **SOC2** | Planned | Timeline available on request |
| **ISO 27001** | Under consideration | - |
| **GDPR** | Ready | Self-hosted deployment supports GDPR compliance (data residency) |
| **HIPAA** | Framework-ready | Self-hosted deployment + proper configuration |

See [Compliance Documentation](data-handling.md) for details.

---

## Security Advisories

Published security advisories will be listed here:

- [GitHub Security Advisories](https://github.com/UAPK/gateway/security/advisories)

**Subscribe:** Watch the repository and enable "Security alerts" notifications.

---

## Bug Bounty Program

**Status:** Not yet active

We're evaluating a bug bounty program for 2025. If you find a vulnerability, we'll:

- Acknowledge your contribution publicly (if desired)
- Provide credit in security advisories
- Consider financial rewards for critical findings (case-by-case)

---

## Acknowledgments

We thank security researchers who responsibly disclose vulnerabilities:

*No vulnerabilities reported yet*

---

## Legal Disclaimer

This software is provided "as is" without warranty of any kind. See [LICENSE](https://github.com/UAPK/gateway/blob/main/LICENSE) for full terms.

**You are responsible for:**
- Securing your deployment
- Compliance with applicable laws and regulations
- Data protection and privacy
- Incident response

UAPK Gateway is a tool for governance and audit, but **you** own the compliance outcomes.

---

## Contact

- **Security reports:** [mail@uapk.info](mailto:mail@uapk.info) (include "SECURITY" in subject)
- **GitHub Security Advisories:** [https://github.com/UAPK/gateway/security/advisories](https://github.com/UAPK/gateway/security/advisories)
- **Response SLA:** 48 hours for security reports

---

## Related

- [Threat Model](threat-model.md) - Detailed threat analysis
- [Data Handling](data-handling.md) - Data protection practices
- [Key Management](key-management.md) - Cryptographic key management
- [Deployment Guide](../deployment/index.md) - Production hardening

# Phase 5: Testing and Validation Plan

## Overview

This document provides a comprehensive testing plan for validating all fixes implemented in Phases 1-4 of the CLEANUP_PLAN. These tests should be executed in the Docker Compose environment with PostgreSQL running.

## Prerequisites

1. Docker and Docker Compose installed
2. All code changes from Phases 1-4 committed
3. Environment variables configured in `.env`

## Phase 5.1: Database Migrations

### Step 1: Verify Migration Files

```bash
# List all migration files
ls -la backend/alembic/versions/

# Expected files:
# - 20241215_000000_0001_initial_schema.py
# - 20241215_000000_0002_add_uapk_manifests.py
# - 20241215_000000_0003_add_capability_tokens.py
# - 20241215_000000_0004_add_audit_log.py
# - 20241215_000000_0005_add_approvals.py
# - 20241215_000000_0006_used_override_tokens.py (NEW)
# - 20241215_000000_0007_add_override_token_fields.py (NEW)
```

### Step 2: Check Current Migration Status

```bash
# Start the database
docker compose up -d postgres

# Check current alembic head
docker compose exec backend alembic heads

# Expected output: Should show current head revision
```

### Step 3: Run Migrations

```bash
# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade 0006 -> 0007, Add override token fields to approvals table
```

### Step 4: Verify Database Schema

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d uapk_gateway

# Verify approvals table has new fields
\d+ approvals

# Expected new columns:
# - override_token_hash (varchar(64), nullable)
# - action_hash (varchar(64), nullable)
# - override_token_expires_at (timestamp with time zone, nullable)
# - override_token_used_at (timestamp with time zone, nullable)

# Verify index exists
\di ix_approvals_override_token_hash

# Verify used_override_tokens table exists
\d+ used_override_tokens

# Exit psql
\q
```

### Success Criteria

- ✅ All migrations run without errors
- ✅ `approvals` table has 4 new override token fields
- ✅ Index `ix_approvals_override_token_hash` exists
- ✅ `used_override_tokens` table exists (from migration 0006)

---

## Phase 5.2: Basic API Functionality

### Step 1: Start All Services

```bash
# Start full stack
docker compose up -d

# Check logs for errors
docker compose logs backend --tail=50

# Expected: No error messages, "Application startup complete"
```

### Step 2: Health Check Endpoints

```bash
# Test liveness probe
curl http://localhost:8000/healthz

# Expected response:
# {"status": "ok"}

# Test readiness probe
curl http://localhost:8000/readyz

# Expected response:
# {"status": "ready", "checks": {"database": true}}
```

### Step 3: API Documentation

```bash
# Access Swagger UI
curl -I http://localhost:8000/docs

# Expected: HTTP 200 OK

# Access OpenAPI spec
curl http://localhost:8000/openapi.json | jq '.paths | keys'

# Expected output should include:
# - "/api/v1/gateway/execute"
# - "/api/v1/gateway/evaluate"
# - "/api/v1/orgs/{org_id}/approvals"
# - "/api/v1/orgs/{org_id}/manifests"
```

### Success Criteria

- ✅ All services start without errors
- ✅ Health endpoints return 200 OK
- ✅ OpenAPI spec includes correct endpoints
- ✅ No `/api/v1/actions` endpoint in spec (deleted in Phase 1)

---

## Phase 5.3: Manifest Registration

### Step 1: Create Test Organization

```bash
# This assumes you have a way to create an org and get an operator token
# Adjust based on your authentication setup

# Create organization (if using a bootstrap script)
docker compose exec backend python scripts/create_org.py test-org

# Or use the API directly with admin credentials
# (Implementation depends on your auth setup)
```

### Step 2: Register a Manifest with Policy and Tools

```bash
# Use one of the updated 47ers examples
MANIFEST_FILE="examples/47ers/general/outbound_email_guard.json"

# Register manifest
curl -X POST http://localhost:8000/api/v1/orgs/${ORG_ID}/manifests \
  -H "Authorization: Bearer ${OPERATOR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @${MANIFEST_FILE}

# Expected response:
# {
#   "manifest_id": "uuid-here",
#   "uapk_id": "outbound-email-guard",
#   "status": "active",
#   "version": "1.0",
#   "created_at": "2025-12-15T...",
#   ...
# }
```

### Step 3: Verify Manifest Loading

```bash
# Check backend logs for manifest validation
docker compose logs backend --tail=100 | grep "manifest_registered"

# Expected: Log entry showing manifest successfully validated and stored
```

### Step 4: Retrieve Manifest

```bash
# Get the registered manifest
curl http://localhost:8000/api/v1/orgs/${ORG_ID}/manifests/${MANIFEST_ID} \
  -H "Authorization: Bearer ${OPERATOR_TOKEN}"

# Expected: Full manifest content including:
# - "policy": { "budgets": {...}, "require_capability_token": true, ... }
# - "tools": { "send": { "type": "webhook", "config": {...} } }
```

### Success Criteria

- ✅ Manifest registration succeeds with policy and tools sections
- ✅ Schema validation passes with `extra="forbid"` (rejects unknown fields)
- ✅ Retrieved manifest matches submitted manifest
- ✅ No validation errors for new `policy` and `tools` sections

---

## Phase 5.4: Gateway Execute Flow with Override Tokens

### Step 1: Test Normal Policy Evaluation

```bash
# Submit an action without override token
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "outbound-email-guard",
    "agent_id": "test-agent",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {
        "to": "test@example.com",
        "subject": "Test",
        "body": "Test email"
      }
    },
    "capability_token": "'"${CAPABILITY_TOKEN}"'"
  }'

# Expected response (if policy requires approval):
# {
#   "interaction_id": "int-xxx",
#   "decision": "deny",
#   "executed": false,
#   "reasons": [
#     {
#       "code": "REQUIRES_APPROVAL",
#       "message": "Action requires human approval"
#     }
#   ]
# }
```

### Step 2: Create Approval with Override Token

```bash
# Approve the action and generate override token
# This would typically be done through the operator UI/API
# For testing, you can create an approval record directly

# Create approval (pseudo-code - adjust to your approval API)
APPROVAL_ID=$(curl -X POST http://localhost:8000/api/v1/orgs/${ORG_ID}/approvals \
  -H "Authorization: Bearer ${OPERATOR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "interaction_id": "'"${INTERACTION_ID}"'",
    "decision": "approved",
    "generate_override_token": true,
    "override_token_expires_in_hours": 24
  }' | jq -r '.approval_id')

# Get the override token from the approval
OVERRIDE_TOKEN=$(curl http://localhost:8000/api/v1/orgs/${ORG_ID}/approvals/${APPROVAL_ID} \
  -H "Authorization: Bearer ${OPERATOR_TOKEN}" \
  | jq -r '.override_token')

echo "Override token: ${OVERRIDE_TOKEN}"
```

### Step 3: Execute Action with Valid Override Token

```bash
# Submit the same action with override token
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "outbound-email-guard",
    "agent_id": "test-agent",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {
        "to": "test@example.com",
        "subject": "Test",
        "body": "Test email"
      }
    },
    "override_token": "'"${OVERRIDE_TOKEN}"'"
  }'

# Expected response:
# {
#   "interaction_id": "int-yyy",
#   "decision": "allow",
#   "executed": true,
#   "result": {
#     "success": true,
#     "data": { ... }
#   },
#   "reasons": [
#     {
#       "code": "OVERRIDE_TOKEN_VALID",
#       "message": "Valid override token from approved action"
#     }
#   ]
# }

# Check database to verify token marked as used
docker compose exec postgres psql -U postgres -d uapk_gateway \
  -c "SELECT override_token_used_at IS NOT NULL as used FROM approvals WHERE approval_id = '${APPROVAL_ID}';"

# Expected: used | t
```

### Step 4: Test Replay Attack Prevention

```bash
# Try to use the same override token again
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "outbound-email-guard",
    "agent_id": "test-agent",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {
        "to": "test@example.com",
        "subject": "Test",
        "body": "Test email"
      }
    },
    "override_token": "'"${OVERRIDE_TOKEN}"'"
  }'

# Expected response:
# {
#   "interaction_id": "int-zzz",
#   "decision": "deny",
#   "executed": false,
#   "reasons": [
#     {
#       "code": "OVERRIDE_TOKEN_ALREADY_USED",
#       "message": "Override token has already been used",
#       "details": {
#         "used_at": "2025-12-15T..."
#       }
#     }
#   ]
# }
```

### Step 5: Test Action Hash Binding

```bash
# Try to use the override token with different action params
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "outbound-email-guard",
    "agent_id": "test-agent",
    "action": {
      "type": "email",
      "tool": "send",
      "params": {
        "to": "different@example.com",
        "subject": "Different Subject",
        "body": "Different body"
      }
    },
    "override_token": "'"${OVERRIDE_TOKEN}"'"
  }'

# Expected response:
# {
#   "interaction_id": "int-aaa",
#   "decision": "deny",
#   "executed": false,
#   "reasons": [
#     {
#       "code": "OVERRIDE_TOKEN_ACTION_MISMATCH",
#       "message": "Override token does not match this action",
#       "details": {
#         "expected_hash": "abc123...",
#         "actual_hash": "def456..."
#       }
#     }
#   ]
# }
```

### Step 6: Test Token Expiration

```bash
# This test requires either:
# 1. Creating an approval with a very short expiration (e.g., 1 second)
# 2. Or manually updating the database to set expiration in the past

# Update approval expiration to the past
docker compose exec postgres psql -U postgres -d uapk_gateway \
  -c "UPDATE approvals SET override_token_expires_at = NOW() - INTERVAL '1 hour' WHERE approval_id = '${EXPIRED_APPROVAL_ID}';"

# Try to use expired token
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "outbound-email-guard",
    "agent_id": "test-agent",
    "action": { ... },
    "override_token": "'"${EXPIRED_OVERRIDE_TOKEN}"'"
  }'

# Expected response:
# {
#   "decision": "deny",
#   "reasons": [
#     {
#       "code": "OVERRIDE_TOKEN_EXPIRED",
#       "message": "Override token has expired",
#       "details": {
#         "expired_at": "2025-12-15T..."
#       }
#     }
#   ]
# }
```

### Success Criteria

- ✅ Normal policy evaluation works (returns DENY for actions requiring approval)
- ✅ Valid override token allows action execution (bypasses policy)
- ✅ Used override token cannot be reused (replay attack prevention)
- ✅ Override token with different action params is rejected (action hash binding)
- ✅ Expired override token is rejected
- ✅ Database correctly records `override_token_used_at` timestamp

---

## Phase 5.5: SSRF Protection Validation

### Step 1: Test Webhook to Public Domain (Should Allow)

```bash
# Create a manifest with webhook to a public test service
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "test-webhook-agent",
    "agent_id": "test-agent",
    "action": {
      "type": "webhook",
      "tool": "public_webhook",
      "params": {
        "url": "https://webhook.site/unique-id",
        "data": {"test": "data"}
      }
    }
  }'

# Expected: Request should succeed (execution allowed)
```

### Step 2: Test Webhook to Localhost (Should Block)

```bash
# Try to send webhook to localhost
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "test-webhook-agent",
    "agent_id": "test-agent",
    "action": {
      "type": "webhook",
      "tool": "malicious_webhook",
      "params": {
        "url": "http://127.0.0.1:5432",
        "data": {"test": "data"}
      }
    }
  }'

# Expected response:
# {
#   "decision": "deny",
#   "executed": false,
#   "result": {
#     "success": false,
#     "error": {
#       "code": "SSRF_BLOCKED",
#       "message": "Access to private/internal IP 127.0.0.1 blocked (SSRF protection)"
#     }
#   }
# }
```

### Step 3: Test Webhook to Private IP (Should Block)

```bash
# Try to send webhook to RFC 1918 private IP
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "test-webhook-agent",
    "agent_id": "test-agent",
    "action": {
      "type": "webhook",
      "tool": "malicious_webhook",
      "params": {
        "url": "http://192.168.1.1/admin",
        "data": {"test": "data"}
      }
    }
  }'

# Expected: SSRF_BLOCKED error with message about private IP
```

### Step 4: Test Webhook to Link-Local IP (Should Block)

```bash
# Try to send webhook to link-local address
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "test-webhook-agent",
    "agent_id": "test-agent",
    "action": {
      "type": "webhook",
      "tool": "malicious_webhook",
      "params": {
        "url": "http://169.254.169.254/latest/meta-data/",
        "data": {"test": "data"}
      }
    }
  }'

# Expected: SSRF_BLOCKED error (AWS metadata service blocked)
```

### Step 5: Test DNS Rebinding Protection

```bash
# Try to use a domain that resolves to a private IP
# Note: This requires setting up a test domain or using a known rebinding domain

# Example with localhost.example.com (if it resolves to 127.0.0.1)
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "test-webhook-agent",
    "agent_id": "test-agent",
    "action": {
      "type": "webhook",
      "tool": "rebinding_webhook",
      "params": {
        "url": "http://localhost.example.com/",
        "data": {"test": "data"}
      }
    }
  }'

# Expected: SSRF_BLOCKED error (DNS resolution catches private IP)
```

### Step 6: Test Domain Allowlist

```bash
# Create a manifest with allowed_domains configuration
# Then test that only allowed domains work

# This requires updating the manifest's tool config:
# "tools": {
#   "webhook": {
#     "type": "webhook",
#     "config": {
#       "allowed_domains": ["webhook.site", "example.com"]
#     }
#   }
# }

# Try allowed domain (should work)
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -d '{ ... "url": "https://webhook.site/..." ... }'

# Expected: Success

# Try disallowed domain (should block)
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -d '{ ... "url": "https://attacker.com/..." ... }'

# Expected: Error message "Domain 'attacker.com' not in allowed list"
```

### Step 7: Test HTTP Request Connector SSRF

```bash
# Test the http_request connector has same protections
curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "test-http-agent",
    "agent_id": "test-agent",
    "action": {
      "type": "http",
      "tool": "api_call",
      "params": {
        "url": "http://10.0.0.1/secret",
        "method": "GET"
      }
    }
  }'

# Expected: SSRF_BLOCKED error for private IP
```

### Success Criteria

- ✅ Public domain webhooks work correctly
- ✅ Localhost (127.0.0.0/8) is blocked
- ✅ RFC 1918 private IPs are blocked (10.x, 172.16.x, 192.168.x)
- ✅ Link-local IPs are blocked (169.254.x)
- ✅ DNS rebinding attacks are prevented (resolution-time IP check)
- ✅ Domain allowlist enforcement works correctly
- ✅ Both webhook and http_request connectors have SSRF protection

---

## Phase 5.6: Comprehensive Test Report

### Generate Test Report

After completing all tests, create a comprehensive report:

```bash
# Create test report file
cat > PHASE5_TEST_REPORT.md <<'EOF'
# Phase 5 Test Report

**Test Date:** [YYYY-MM-DD]
**Tester:** [Name]
**Environment:** Docker Compose (local)

## Summary

- Total Tests: [X]
- Passed: [X]
- Failed: [X]
- Skipped: [X]

## Phase 5.1: Database Migrations

| Test | Status | Notes |
|------|--------|-------|
| Migration files present | ✅ PASS | All 7 migration files found |
| Migrations run successfully | ✅ PASS | No errors during upgrade |
| Approvals table has override fields | ✅ PASS | 4 new fields added |
| Index on override_token_hash exists | ✅ PASS | Index created successfully |

## Phase 5.2: Basic API Functionality

| Test | Status | Notes |
|------|--------|-------|
| Services start without errors | ✅ PASS | All containers healthy |
| /healthz returns 200 | ✅ PASS | Liveness probe working |
| /readyz returns 200 | ✅ PASS | Readiness probe working |
| OpenAPI spec correct | ✅ PASS | Gateway endpoints present |
| Old /api/v1/actions deleted | ✅ PASS | Endpoint not in spec |

## Phase 5.3: Manifest Registration

| Test | Status | Notes |
|------|--------|-------|
| Manifest with policy accepted | ✅ PASS | Schema validation passed |
| Manifest with tools accepted | ✅ PASS | Tool configs loaded |
| extra="forbid" rejects unknown fields | ✅ PASS | Validation error on extra fields |
| Retrieved manifest matches submitted | ✅ PASS | Full content preserved |

## Phase 5.4: Override Token Security

| Test | Status | Notes |
|------|--------|-------|
| Normal policy evaluation works | ✅ PASS | DENY for actions requiring approval |
| Valid override token allows execution | ✅ PASS | Policy bypassed correctly |
| Replay attack prevented | ✅ PASS | Used token rejected |
| Action hash binding enforced | ✅ PASS | Different params rejected |
| Expired token rejected | ✅ PASS | Expiration check working |
| Token usage recorded in DB | ✅ PASS | Timestamp set correctly |

## Phase 5.5: SSRF Protection

| Test | Status | Notes |
|------|--------|-------|
| Public domain allowed | ✅ PASS | webhook.site worked |
| Localhost blocked | ✅ PASS | 127.0.0.1 rejected |
| RFC 1918 IPs blocked | ✅ PASS | 192.168.x, 10.x, 172.16.x rejected |
| Link-local blocked | ✅ PASS | 169.254.x rejected |
| DNS rebinding prevented | ✅ PASS | Resolution-time IP check |
| Domain allowlist enforced | ✅ PASS | Only allowed domains work |
| HTTP connector protected | ✅ PASS | Same SSRF checks applied |

## Issues Found

[Document any issues discovered during testing]

## Recommendations

[Any additional improvements or observations]

## Sign-off

- [ ] All critical tests passing
- [ ] No blocking issues found
- [ ] Ready for production deployment

**Tester Signature:** ___________________
**Date:** ___________________
EOF
```

### Generate Metrics

```bash
# Query database for validation metrics
docker compose exec postgres psql -U postgres -d uapk_gateway <<'SQL'
-- Count manifests with policy sections
SELECT COUNT(*) as manifests_with_policy
FROM uapk_manifests
WHERE manifest_content->>'policy' IS NOT NULL;

-- Count approvals with override tokens
SELECT COUNT(*) as approvals_with_override_tokens
FROM approvals
WHERE override_token_hash IS NOT NULL;

-- Count used override tokens
SELECT COUNT(*) as used_override_tokens
FROM approvals
WHERE override_token_used_at IS NOT NULL;

-- SSRF blocks (check audit logs if available)
SELECT COUNT(*) as ssrf_blocks
FROM audit_log
WHERE metadata->>'error_code' = 'SSRF_BLOCKED';
SQL
```

---

## Rollback Procedure

If any critical issues are found during testing:

### 1. Rollback Database Migrations

```bash
# Downgrade to before Phase 3 migrations
docker compose exec backend alembic downgrade 0005

# Verify rollback
docker compose exec postgres psql -U postgres -d uapk_gateway \
  -c "\d approvals" | grep override_token

# Expected: No override_token columns
```

### 2. Rollback Code Changes

```bash
# List commits from cleanup phases
git log --oneline --all | grep -E "Phase [1-4]"

# Revert to before cleanup started
git revert <commit-hash-of-phase-4> <commit-hash-of-phase-3> <commit-hash-of-phase-2> <commit-hash-of-phase-1>

# Or hard reset (USE WITH CAUTION)
git reset --hard <commit-before-cleanup>

# Restart services
docker compose down
docker compose up -d
```

### 3. Verify Rollback

```bash
# Check that old endpoints are back (if rolled back Phase 1)
curl http://localhost:8000/openapi.json | jq '.paths | keys' | grep actions

# Check that manifests don't have policy sections (if rolled back Phase 2)
# Check that SSRF protection is disabled (if rolled back Phase 3)
```

---

## Performance Benchmarks (Optional)

### Gateway Throughput Test

```bash
# Use Apache Bench or similar tool
ab -n 1000 -c 10 \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -H "Content-Type: application/json" \
  -p gateway_request.json \
  http://localhost:8000/api/v1/gateway/execute

# Expected: <100ms p95 latency for policy evaluation
```

### DNS Resolution Overhead Test

```bash
# Compare performance with and without DNS resolution
# This measures the overhead of SSRF protection

# Time webhook to public domain (with DNS check)
time curl -X POST http://localhost:8000/api/v1/gateway/execute \
  -H "X-API-Key: ${AGENT_API_KEY}" \
  -d '{ ... "url": "https://webhook.site/..." ... }'

# Expected: <50ms overhead for DNS resolution
```

---

## Appendix: Test Data

### Sample Manifest with Policy and Tools

```json
{
  "version": "1.0",
  "agent": {
    "id": "test-agent",
    "name": "Test Agent",
    "version": "1.0.0",
    "description": "Agent for testing",
    "organization": "test-org"
  },
  "capabilities": {
    "requested": ["email:send", "webhook:call"]
  },
  "policy": {
    "budgets": {
      "email:send": {
        "daily_limit": 10,
        "hourly_limit": 5
      }
    },
    "require_capability_token": true,
    "tool_allowlist": ["send", "webhook"]
  },
  "tools": {
    "send": {
      "type": "webhook",
      "config": {
        "url": "https://webhook.site/test-id",
        "allowed_domains": ["webhook.site"]
      }
    }
  }
}
```

### Sample Gateway Request

```json
{
  "uapk_id": "test-agent",
  "agent_id": "test-agent",
  "action": {
    "type": "email",
    "tool": "send",
    "params": {
      "to": "test@example.com",
      "subject": "Test Email",
      "body": "This is a test"
    }
  },
  "capability_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...",
  "context": {
    "conversation_id": "conv-123",
    "reason": "User requested notification"
  }
}
```

### Sample Override Token Request

```json
{
  "uapk_id": "test-agent",
  "agent_id": "test-agent",
  "action": {
    "type": "email",
    "tool": "send",
    "params": {
      "to": "test@example.com",
      "subject": "Test Email",
      "body": "This is a test"
    }
  },
  "override_token": "ot_abc123def456..."
}
```

---

## End of Testing Plan

This plan should be executed in sequence. All tests in a phase should pass before moving to the next phase. Document all results in the test report template provided in Phase 5.6.

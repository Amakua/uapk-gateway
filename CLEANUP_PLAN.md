# UAPK Gateway P0 Cleanup Implementation Plan

## Executive Summary

This plan addresses 7 critical (P0) issues identified in the technical review that prevent the gateway from functioning end-to-end and create security vulnerabilities.

**Timeline:** 6-8 hours of focused work
**Goal:** Production-ready foundation for pilot demos

---

## Phase 1: Remove Confusion & Dead Code (1-2 hours)

### Objective
Eliminate competing architectures by removing the old gateway path and consolidating on the new `GatewayService + PolicyEngine` approach.

### Tasks

#### 1.1: Archive Old Gateway Path
**Files to modify/move:**
- `backend/app/api/v1/actions.py` → DELETE or move to `backend/legacy/`
- `backend/app/services/action_gateway.py` → DELETE or move to `backend/legacy/`
- `backend/app/services/policy_service.py` → DELETE (replaced by PolicyEngine)
- `backend/app/services/policy_evaluator.py` → DELETE (replaced by PolicyEngine)

**Validation:**
- [ ] No imports of deleted modules remain
- [ ] API router in `backend/app/main.py` doesn't include old actions router
- [ ] Tests still pass (delete tests for removed code)

#### 1.2: Remove HS256 Capability Token Flow
**Files to modify:**
- `backend/app/services/capability_token_service.py` → REVIEW and potentially DELETE
  - Keep only if it's a wrapper around Ed25519 JWT flow
  - Delete if it's the old HS256 implementation
- `backend/app/core/security.py` → Remove JWT creation functions using HS256
- Database: Keep `capability_tokens` table for now (stores issued Ed25519 tokens)

**Decision point:** Verify `CapabilityTokenService` is compatible with Ed25519 approach before deleting.

**Validation:**
- [ ] All capability token operations use Ed25519
- [ ] No HS256 JWT creation remains

#### 1.3: Fix `default_org_id` Assumption
**Problem:** `User` model has no `default_org_id` field, but code assumes it exists.

**Option A (Recommended - Path Parameters):**
Change all routes to require explicit `org_id` in path.

**Files to modify:**
1. `backend/app/api/v1/approvals.py`
   - **Before:** `current_user.default_org_id`
   - **After:** Path parameter `org_id: int` + `RequireOrgOperator` dependency

2. `backend/app/api/v1/capabilities.py`
   - Same change for issuer routes

3. `backend/app/ui/routes.py`
   - Add org selection UI or default to first org from memberships

**Example change:**
```python
# BEFORE
@router.get("/approvals/")
async def list_approvals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org_id = current_user.default_org_id  # BREAKS

# AFTER
@router.get("/orgs/{org_id}/approvals/")
async def list_approvals(
    org_id: int,
    current_user: User = Depends(RequireOrgOperator(org_id)),
    db: Session = Depends(get_db)
):
    # org_id from path, membership verified by dependency
```

**Alternative Option B (Add default_org_id field):**
- Add migration to add `default_org_id` column to `users` table
- NOT RECOMMENDED: adds complexity for minimal benefit

**Validation:**
- [ ] All approvals routes work with explicit org_id
- [ ] All capabilities routes work with explicit org_id
- [ ] UI dashboard loads without errors
- [ ] RBAC enforcement works (non-members can't access)

---

## Phase 2: Fix Manifest/Gateway Integration (2-3 hours)

### Objective
Align manifest schema with what gateway execution code expects (`tools` and `policy` sections).

### Approach: Option A (Extend Manifest Schema)
Faster, works for MVP demos.

### Tasks

#### 2.1: Update Manifest Pydantic Schema
**File:** `backend/app/schemas/manifest.py`

**Current structure:**
```python
class ManifestContent(BaseModel):
    agent_identity: AgentIdentity
    requested_capabilities: List[CapabilityRequest]
    constraints: Optional[Constraints] = None
```

**New structure:**
```python
class PolicyConfig(BaseModel):
    """Policy configuration for gateway decisions."""
    budgets: Optional[Dict[str, Any]] = None
    counterparty_allowlist: Optional[List[str]] = None
    counterparty_denylist: Optional[List[str]] = None
    jurisdiction_allowlist: Optional[List[str]] = None
    tool_allowlist: Optional[List[str]] = None
    tool_denylist: Optional[List[str]] = None
    amount_caps: Optional[Dict[str, float]] = None
    require_capability_token: bool = False

class ToolConfig(BaseModel):
    """Tool configuration for gateway execution."""
    type: str  # "http_request", "webhook", "mock"
    config: Dict[str, Any]  # connector-specific config

class ManifestContent(BaseModel):
    agent_identity: AgentIdentity
    requested_capabilities: List[CapabilityRequest]
    constraints: Optional[Constraints] = None
    policy: Optional[PolicyConfig] = None  # NEW
    tools: Optional[Dict[str, ToolConfig]] = None  # NEW

    model_config = ConfigDict(extra="forbid")  # Strict validation
```

#### 2.2: Update JSON Schema
**File:** `schemas/manifest.v1.schema.json`

Merge structure from `uapk-manifest.v0.1.schema.json` into v1 schema to include:
- `policy` object with budget/allowlist/denylist fields
- `tools` object with connector configurations

#### 2.3: Update Example Manifests (47ers)
**Files:** All files in `examples/47ers/`

Add `policy` and `tools` sections to each example:

```yaml
# Example: outbound_email_guard.yaml
agent_identity:
  agent_id: "email-assistant-v1"
  # ...

policy:
  tool_allowlist: ["send_email"]
  counterparty_denylist: ["competitor.com"]
  budgets:
    send_email:
      daily_limit: 50

tools:
  send_email:
    type: "webhook"
    config:
      url: "https://api.sendgrid.com/v3/mail/send"
      method: "POST"
      allowed_domains: ["api.sendgrid.com"]
```

**Files to update:**
- `examples/47ers/general/outbound_email_guard.yaml`
- `examples/47ers/finance/trading_execution_gate.yaml`
- `examples/47ers/legal/settlement_negotiation.yaml`
- All other 47er examples

#### 2.4: Update Manifest Service
**File:** `backend/app/services/manifest_service.py`

Ensure `create_manifest()` and `update_manifest()` properly serialize the extended schema:

```python
def create_manifest(self, data: ManifestCreate) -> Manifest:
    # Validate with new schema (will fail if extra keys present)
    manifest_data = data.manifest.model_dump(mode="json")

    # Store as JSON (includes policy + tools)
    manifest_obj = Manifest(
        uapk_id=data.uapk_id,
        version=data.version,
        manifest_json=manifest_data,  # Full schema
        organization_id=data.organization_id
    )
    # ...
```

#### 2.5: Update Gateway Service to Use Manifest Policy/Tools
**File:** `backend/app/services/gateway_service.py`

Currently expects `manifest_json.get("policy", {})` - ensure this works with new schema:

```python
async def evaluate_action(self, request: GatewayEvaluateRequest) -> GatewayEvaluateResponse:
    # Load manifest
    manifest = self.manifest_service.get_active_manifest(uapk_id)
    manifest_json = manifest.manifest_json

    # Extract policy (now guaranteed to be present if validated)
    policy_config = manifest_json.get("policy", {})

    # Pass to PolicyEngine
    decision = await self.policy_engine.evaluate(
        action_type=request.action_type,
        tool=request.tool,
        params=request.parameters,
        policy_rules=policy_config,
        # ...
    )
```

**Validation:**
- [ ] Manifest creation validates policy/tools schema
- [ ] Gateway can load policy from manifest
- [ ] Gateway can load tool configs from manifest
- [ ] Example manifests pass validation

---

## Phase 3: Security Lockdown (1-2 hours)

### Objective
Fix critical security vulnerabilities: SSRF, weak approval tokens, broken endpoints.

### Tasks

#### 3.1: Fix WebhookConnector SSRF Vulnerability
**File:** `backend/app/connectors/webhook_connector.py`

**Current code:** No URL validation

**New code:**
```python
import ipaddress
from urllib.parse import urlparse

class WebhookConnector(BaseConnector):
    BLOCKED_HOSTS = ['localhost', '127.0.0.1', '::1', '0.0.0.0']
    BLOCKED_RANGES = [
        ipaddress.ip_network('10.0.0.0/8'),
        ipaddress.ip_network('172.16.0.0/12'),
        ipaddress.ip_network('192.168.0.0/16'),
        ipaddress.ip_network('169.254.0.0/16'),  # Link-local
        ipaddress.ip_network('fd00::/8'),  # IPv6 ULA
    ]

    def __init__(self, config: Dict[str, Any]):
        self.url = config["url"]
        self.allowed_domains = config.get("allowed_domains", [])
        self._validate_url()

    def _validate_url(self):
        """Prevent SSRF attacks."""
        parsed = urlparse(self.url)

        # Block non-HTTP schemes
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}")

        # Block localhost variants
        if parsed.hostname in self.BLOCKED_HOSTS:
            raise ValueError(f"Blocked hostname: {parsed.hostname}")

        # Block private IP ranges
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            for blocked_range in self.BLOCKED_RANGES:
                if ip in blocked_range:
                    raise ValueError(f"Blocked IP range: {ip}")
        except ValueError:
            pass  # Not an IP, continue with domain check

        # Enforce allowlist if configured
        if self.allowed_domains:
            if not any(parsed.hostname.endswith(domain) for domain in self.allowed_domains):
                raise ValueError(f"Domain not in allowlist: {parsed.hostname}")
```

**Validation:**
- [ ] Webhook connector blocks localhost
- [ ] Webhook connector blocks private IPs
- [ ] Webhook connector enforces allowlist
- [ ] Valid webhooks still work

#### 3.2: Fix Approval Override Token Enforcement
**Files to modify:**
1. `backend/app/services/gateway_service.py` - Add action hash computation
2. `backend/app/services/capability_service.py` - Validate action_hash claim
3. `backend/app/models/approval.py` - Add token usage tracking

**Step 1: Define canonical action hash function**
```python
# backend/app/core/hashing.py (new file)
import hashlib
import json
from typing import Any, Dict

def compute_action_hash(
    action_type: str,
    tool: str,
    parameters: Dict[str, Any],
    counterparty: str = None,
    context: Dict[str, Any] = None
) -> str:
    """
    Compute canonical hash of an action for approval binding.

    Ensures two identical actions produce the same hash.
    """
    canonical_action = {
        "action_type": action_type,
        "tool": tool,
        "parameters": parameters,
        "counterparty": counterparty,
        "context": context or {}
    }

    # Canonical JSON (sorted keys, no whitespace)
    canonical_json = json.dumps(canonical_action, sort_keys=True, separators=(',', ':'))

    # SHA-256 hash
    return hashlib.sha256(canonical_json.encode()).hexdigest()
```

**Step 2: Validate override token contains matching action_hash**
```python
# backend/app/services/gateway_service.py
from app.core.hashing import compute_action_hash

async def execute_action(self, request: GatewayExecuteRequest) -> GatewayExecuteResponse:
    # Compute action hash for this request
    action_hash = compute_action_hash(
        action_type=request.action_type,
        tool=request.tool,
        parameters=request.parameters,
        counterparty=request.counterparty,
        context=request.context
    )

    # If override token provided, validate it
    if request.override_token:
        token_claims = self.capability_service.verify_override_token(request.override_token)

        # CRITICAL: Check action_hash matches
        if token_claims.get("action_hash") != action_hash:
            raise ValueError("Override token does not match requested action")

        # Check one-time use (new table: used_tokens)
        if self._is_token_used(token_claims["jti"]):
            raise ValueError("Override token already used")

        # Mark token as used
        self._mark_token_used(token_claims["jti"])
```

**Step 3: Add token usage tracking**
```python
# Alembic migration: add used_override_tokens table
"""
CREATE TABLE used_override_tokens (
    id SERIAL PRIMARY KEY,
    token_jti VARCHAR NOT NULL UNIQUE,
    used_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approval_id INTEGER REFERENCES approvals(id),
    action_hash VARCHAR NOT NULL
);
CREATE INDEX idx_token_jti ON used_override_tokens(token_jti);
"""
```

**Validation:**
- [ ] Override token must contain action_hash
- [ ] Action hash is computed and validated
- [ ] Tokens can only be used once
- [ ] Replay attack blocked

#### 3.3: Fix Gateway Public Key Endpoint
**File:** `backend/app/api/v1/capabilities.py`

**Before:**
```python
key_base64 = key_manager.get_public_key_base64()  # BREAKS
```

**After:**
```python
key_base64 = key_manager.public_key_base64  # Property, not method
```

**Validation:**
- [ ] GET `/api/v1/capabilities/gateway-key` returns valid base64 key
- [ ] Key can be used to verify gateway signatures

---

## Phase 4: Documentation Sync (1 hour)

### Objective
Ensure all documentation matches actual API behavior.

### Tasks

#### 4.1: Update API Endpoint Paths
**Files to update:**
- `docs/api/*.md`
- `README.md`
- `docs/quickstart.md`
- `examples/` (curl examples)

**Changes:**
- `/v1/...` → `/api/v1/...` everywhere
- Update all endpoint examples

#### 4.2: Fix Authentication Header Examples
**Before:**
```bash
curl -H "Authorization: Bearer $API_KEY"
```

**After:**
```bash
curl -H "X-API-Key: $API_KEY"
```

**Files to update:**
- `docs/api/gateway.md`
- `docs/quickstart.md`
- `examples/` scripts

#### 4.3: Remove References to Old `/actions` Endpoint
Search and replace:
- `/api/v1/actions` → `/api/v1/gateway/execute`
- Update all references to old gateway flow

**Files to update:**
- `docs/api/gateway.md`
- `docs/concepts/manifest.md`
- `README.md`

#### 4.4: Update Manifest Documentation
**File:** `docs/concepts/manifest.md`

Add documentation for new `policy` and `tools` sections with examples.

**Validation:**
- [ ] All endpoint paths are correct
- [ ] All auth header examples are correct
- [ ] No references to deleted endpoints
- [ ] Manifest docs show policy/tools structure

---

## Phase 5: Testing & Validation (1 hour)

### Objective
Ensure end-to-end flows work after cleanup.

### Test Scenarios

#### 5.1: Manifest Creation with Policy/Tools
```python
# Test: Create manifest with full schema
manifest_data = {
    "agent_identity": {...},
    "requested_capabilities": [...],
    "policy": {
        "budgets": {"send_email": {"daily_limit": 50}},
        "counterparty_denylist": ["evil.com"]
    },
    "tools": {
        "send_email": {
            "type": "webhook",
            "config": {
                "url": "https://api.sendgrid.com/v3/mail/send",
                "allowed_domains": ["api.sendgrid.com"]
            }
        }
    }
}

# Should succeed
manifest = manifest_service.create_manifest(manifest_data)
```

#### 5.2: Gateway Execution with Approval Override
```python
# Test: Execute action with override token
# 1. Create action that requires approval
# 2. Get approval with override token
# 3. Execute with override token (should succeed)
# 4. Try to reuse token (should fail - replay protection)
```

#### 5.3: SSRF Protection
```python
# Test: Webhook connector blocks private IPs
webhook_config = {
    "url": "http://169.254.169.254/latest/meta-data",
    "allowed_domains": []
}
# Should raise ValueError
connector = WebhookConnector(webhook_config)
```

#### 5.4: Org-Scoped Routes
```python
# Test: User can only access their org's approvals
# 1. Create approval in org_id=1
# 2. Try to access as user in org_id=2 (should fail with 403)
```

### Validation Checklist
- [ ] All unit tests pass
- [ ] Integration test: Create manifest → Execute action
- [ ] Integration test: Create approval → Use override token
- [ ] SSRF protection blocks private IPs
- [ ] Org isolation enforced (no cross-org access)
- [ ] Gateway signature verification works
- [ ] Audit log hash chain valid

---

## Implementation Order

### Day 1 (4-5 hours)
1. Phase 1.1-1.2: Delete old gateway code (30 min)
2. Phase 1.3: Fix default_org_id (1-1.5 hours)
3. Phase 2.1-2.2: Update manifest schema (1 hour)
4. Phase 2.3: Update example manifests (1 hour)
5. Phase 3.3: Fix public key endpoint (15 min)

### Day 2 (3-4 hours)
6. Phase 3.1: Fix SSRF vulnerability (1 hour)
7. Phase 3.2: Fix approval override tokens (1.5 hours)
8. Phase 4: Documentation sync (1 hour)
9. Phase 5: Testing & validation (1 hour)

---

## Success Criteria

After completion:
- ✅ Single, coherent gateway architecture (new path only)
- ✅ No runtime crashes from missing fields
- ✅ Manifest schema matches gateway expectations
- ✅ SSRF vulnerability fixed
- ✅ Approval override tokens properly enforced
- ✅ All docs match actual behavior
- ✅ End-to-end demo works: create manifest → execute action → audit log

---

## Risk Mitigation

### Rollback Strategy
- Tag current state before starting: `git tag pre-cleanup-$(date +%Y%m%d)`
- Each phase is independently committable
- If a phase breaks, revert that commit and continue

### Breaking Changes
The `default_org_id` fix will break existing UI code. Options:
1. Add shim: first membership's org_id becomes default
2. Require org selection on login
3. URL parameter `/dashboard?org_id=1`

**Recommendation:** Option 3 (URL parameter) - cleanest and most explicit.

---

## Files Modified Summary

**Backend Code:**
- `backend/app/api/v1/approvals.py` - org_id path params
- `backend/app/api/v1/capabilities.py` - org_id path params, fix public key endpoint
- `backend/app/schemas/manifest.py` - extend schema (policy/tools)
- `backend/app/services/gateway_service.py` - action hash validation
- `backend/app/connectors/webhook_connector.py` - SSRF protection
- `backend/app/core/hashing.py` - NEW: canonical action hash
- `backend/app/main.py` - remove old router imports

**Database:**
- Migration: `used_override_tokens` table

**Schemas:**
- `schemas/manifest.v1.schema.json` - add policy/tools

**Examples:**
- All files in `examples/47ers/` - add policy/tools sections

**Documentation:**
- `docs/api/*.md` - fix paths, auth headers
- `docs/concepts/manifest.md` - document policy/tools
- `README.md` - fix quickstart examples

**Deleted:**
- `backend/app/api/v1/actions.py`
- `backend/app/services/action_gateway.py`
- `backend/app/services/policy_service.py`
- `backend/app/services/policy_evaluator.py`

---

## Post-Cleanup Architecture

```
┌─────────────────────────────────────────┐
│         UAPK Gateway (Clean)            │
├─────────────────────────────────────────┤
│                                         │
│  ┌────────────────────────────────┐    │
│  │  API Layer                     │    │
│  │  - /api/v1/orgs/{id}/approvals │    │
│  │  - /api/v1/gateway/execute     │    │
│  │  - X-API-Key auth              │    │
│  └────────────────────────────────┘    │
│              ↓                          │
│  ┌────────────────────────────────┐    │
│  │  GatewayService                │    │
│  │  - Action hash computation     │    │
│  │  - Override token validation   │    │
│  └────────────────────────────────┘    │
│              ↓                          │
│  ┌────────────────────────────────┐    │
│  │  PolicyEngine                  │    │
│  │  - Reads manifest.policy       │    │
│  │  - Deterministic decisions     │    │
│  └────────────────────────────────┘    │
│              ↓                          │
│  ┌────────────────────────────────┐    │
│  │  Connectors (SSRF-safe)        │    │
│  │  - WebhookConnector (fixed)    │    │
│  │  - HttpRequestConnector        │    │
│  └────────────────────────────────┘    │
│              ↓                          │
│  ┌────────────────────────────────┐    │
│  │  Audit Log (Ed25519)           │    │
│  │  - Hash chain                  │    │
│  │  - Gateway signatures          │    │
│  └────────────────────────────────┘    │
│                                         │
└─────────────────────────────────────────┘
```

Single flow, no competing paths, secure by default.

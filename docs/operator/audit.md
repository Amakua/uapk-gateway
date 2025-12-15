---
title: Audit & Compliance
description: Viewing logs and verifying chain integrity
---

# Audit & Compliance

UAPK Gateway maintains tamper-evident audit logs for every action. This guide covers viewing, exporting, and verifying logs.

## Viewing Logs

### Log Explorer

Navigate to **Logs** in the sidebar or press `l`.

```
┌────────────────────────────────────────────────────────────────────────────┐
│ AUDIT LOGS                                                        [Export] │
├────────────────────────────────────────────────────────────────────────────┤
│ Filter: [Agent ▼] [Action ▼] [Decision ▼] [Date Range ▼]        [Search]  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  int-abc123  10:32:15  customer-support-bot  email:send     ✓ approved     │
│  int-abc122  10:31:42  customer-support-bot  crm:update     ✓ approved     │
│  int-abc121  10:30:18  deployment-bot        k8s:deploy     ⏳ pending     │
│  int-abc120  10:29:55  customer-support-bot  crm:delete     ✗ denied       │
│  int-abc119  10:28:33  deployment-bot        github:read    ✓ approved     │
│                                                                             │
│                                                      [← Prev] [Next →]     │
└────────────────────────────────────────────────────────────────────────────┘
```

### Filtering Logs

| Filter | Options |
|--------|---------|
| Agent | Select specific agent(s) |
| Action | email, crm, kubernetes, etc. |
| Decision | approved, denied, pending |
| Date Range | Last hour, today, week, custom |

### CLI Filtering

```bash
# Filter by agent and decision
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/logs?uapk_id=customer-support-bot&decision=denied" \
  -H "Authorization: Bearer $TOKEN"

# Filter by time range
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/logs?from=2024-12-01T00:00:00Z&to=2024-12-14T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

## Log Record Details

Click a record to view full details:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ LOG RECORD                                                    int-abc123   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Record ID:    int-abc123                                                  │
│  Agent:        customer-support-bot                                        │
│  Action:       email:send                                                  │
│  Decision:     ✓ approved                                                  │
│  Timestamp:    2024-12-14 10:32:15 UTC                                     │
│                                                                             │
│  HASHES                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Request Hash:   sha256:a1b2c3d4e5f6...                               │  │
│  │ Result Hash:    sha256:g7h8i9j0k1l2...                               │  │
│  │ Record Hash:    sha256:m3n4o5p6q7r8...                               │  │
│  │ Previous Hash:  sha256:s9t0u1v2w3x4...                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  REQUEST                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ {                                                                    │  │
│  │   "to": "customer@example.com",                                      │  │
│  │   "subject": "Re: Your inquiry",                                     │  │
│  │   "body": "Thank you for contacting us..."                           │  │
│  │ }                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  RESULT                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ {                                                                    │  │
│  │   "success": true,                                                   │  │
│  │   "message_id": "msg-xyz789"                                         │  │
│  │ }                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  POLICY TRACE                                                               │
│  ✓ manifest_validation: pass                                               │
│  ✓ capability_token: pass                                                  │
│  ✓ action_type: pass                                                       │
│  ✓ tool_authorization: pass                                                │
│  ✓ budget_check: pass (45/100)                                             │
│                                                                             │
│  SIGNATURE                                                                  │
│  ✓ Valid Ed25519 signature                                                 │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

## Chain Verification

### Dashboard Verification

Navigate to **Logs → Verify** to check chain integrity:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ CHAIN VERIFICATION                                                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Select Agent: [customer-support-bot ▼]                    [Verify Chain]  │
│                                                                             │
│  Last Verification: 2024-12-14 06:00:00 UTC (6 hours ago)                  │
│  Status: ✓ Valid                                                           │
│  Records: 1,250                                                            │
│                                                                             │
│  VERIFICATION RESULT                                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ ✓ Chain Integrity: All records linked correctly                      │  │
│  │ ✓ Hash Verification: All record hashes match                         │  │
│  │ ✓ Signature Verification: All signatures valid                       │  │
│  │                                                                       │  │
│  │ First Record: int-001  (2024-01-15 08:00:00)                         │  │
│  │ Last Record:  int-1250 (2024-12-14 10:32:15)                         │  │
│  │                                                                       │  │
│  │ First Hash: sha256:a1b2c3d4...                                       │  │
│  │ Last Hash:  sha256:x7y8z9a0...                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### CLI Verification

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/logs/verify/customer-support-bot \
  -H "Authorization: Bearer $TOKEN"
```

### Automated Verification

Set up scheduled verification:

```bash
# Add to crontab for daily verification
0 6 * * * curl -X GET http://localhost:8000/api/v1/orgs/$ORG_ID/logs/verify/all \
  -H "Authorization: Bearer $TOKEN" | jq '.is_valid' || notify-team "Chain verification failed"
```

## Exporting Logs

### JSON Export

Export logs with full verification data:

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/logs/export/download \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "uapk_id": "customer-support-bot",
    "from": "2024-12-01T00:00:00Z",
    "to": "2024-12-14T23:59:59Z",
    "include_manifest": true
  }' \
  > export.json
```

### JSONL Export

For streaming/large exports:

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/logs/export/jsonl \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"uapk_id": "customer-support-bot"}' \
  > logs.jsonl
```

## Offline Verification

Verify exported logs without gateway access:

```bash
# Download verification script
curl -O https://gateway.example.com/scripts/verify_log_chain.py

# Run verification
python verify_log_chain.py export.json
```

Output:

```
UAPK Gateway Log Chain Verification
====================================

Loading export file: export.json
Export ID: exp-abc123
Agent: customer-support-bot
Records: 500

Verifying chain integrity...
  [1/500] int-001... OK
  [2/500] int-002... OK
  ...
  [500/500] int-500... OK

Verifying signatures...
  Using gateway public key: MCowBQYDK2VwAyEA...
  [1/500] int-001... OK
  ...

============================================
VERIFICATION PASSED

Summary:
  Records verified: 500
  First record: int-001
  Last record: int-500
  First hash: sha256:a1b2c3...
  Last hash: sha256:x7y8z9...
  All signatures valid: Yes
============================================
```

## Compliance Reports

### Generate Report

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/reports/compliance \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from": "2024-12-01T00:00:00Z",
    "to": "2024-12-31T23:59:59Z",
    "include_verification": true
  }' \
  > compliance-report.json
```

### Report Contents

- Organization summary
- Agent inventory with capabilities
- Action summary by type and decision
- Approval statistics
- Chain verification status
- Policy violations

## Audit Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| Chain verification | Daily | `logs/verify/{uapk_id}` |
| Log export | Weekly | `logs/export/download` |
| Compliance report | Monthly | `reports/compliance` |
| Archive to cold storage | Quarterly | Custom script |

## Best Practices

!!! tip "Regular Verification"
    Run chain verification daily as part of compliance checks.

!!! tip "Secure Exports"
    Store exported logs in secure, encrypted storage.

!!! tip "Retention Policy"
    Define and enforce log retention based on compliance requirements.

!!! warning "Protect Gateway Keys"
    The Ed25519 signing key is critical. See [Key Management](../security/key-management.md).

## Related

- [Audit Logs](../concepts/logs.md) - Log concepts
- [API: Logs](../api/logs.md) - API reference
- [Security](../security/index.md) - Security practices

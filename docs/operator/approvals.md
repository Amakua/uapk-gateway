---
title: Managing Approvals
description: Review and act on escalated requests
---

# Managing Approvals

When the policy engine returns ESCALATE, an approval task is created for operator review.

## Approval Queue

### Accessing the Queue

Navigate to **Approvals** in the sidebar or press `a`.

```
┌────────────────────────────────────────────────────────────────────────────┐
│ APPROVALS                                          [Pending] [All] [Stats] │
├────────────────────────────────────────────────────────────────────────────┤
│ Filter: [Status ▼] [Agent ▼] [Action ▼] [Date Range ▼]          [Search]  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ⏳ appr-xyz789  deployment-bot  k8s:deploy  REQUIRES_APPROVAL   2h ago    │
│     Deploy app:v2.0.0 to production namespace                              │
│                                                            [Review →]      │
│                                                                             │
│  ⏳ appr-abc123  customer-bot    crm:delete  AMOUNT_THRESHOLD    4h ago    │
│     Delete 500 records matching filter                                     │
│                                                            [Review →]      │
│                                                                             │
│  ⏳ appr-def456  analytics-bot   export:run  NEW_COUNTERPARTY    1d ago    │
│     Export data to partner-api.example.com                                 │
│                                                            [Review →]      │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

## Reviewing a Request

Click **Review** to open the approval details:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ APPROVAL DETAIL                                              appr-xyz789   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Agent:      deployment-bot (Deployment Bot v2.1.0)                        │
│  Action:     kubernetes:deploy                                              │
│  Status:     ⏳ Pending                                                     │
│  Created:    2024-12-14 10:00:00 (2 hours ago)                             │
│  Expires:    2024-12-15 10:00:00 (22 hours remaining)                      │
│                                                                             │
│  REASON                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ REQUIRES_APPROVAL: Action 'kubernetes:deploy' requires human        │  │
│  │ approval per manifest constraints                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  REQUEST PARAMETERS                                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ {                                                                    │  │
│  │   "namespace": "production",                                         │  │
│  │   "image": "app:v2.0.0",                                             │  │
│  │   "replicas": 3,                                                     │  │
│  │   "resources": {                                                     │  │
│  │     "cpu": "500m",                                                   │  │
│  │     "memory": "512Mi"                                                │  │
│  │   }                                                                  │  │
│  │ }                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  POLICY TRACE                                                               │
│  ✓ manifest_validation: pass                                               │
│  ✓ capability_token: pass                                                  │
│  ✓ action_type: pass                                                       │
│  ⚠ tool_authorization: escalate (requires approval)                       │
│                                                                             │
│  RISK SNAPSHOT                                                              │
│  Budget: 12/50 actions (24%)                                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐
│  │ Notes:                                                                   │
│  │ ┌───────────────────────────────────────────────────────────────────┐   │
│  │ │                                                                   │   │
│  │ └───────────────────────────────────────────────────────────────────┘   │
│  │                                                                          │
│  │              [Deny]                              [Approve]               │
│  └─────────────────────────────────────────────────────────────────────────┘
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

## Approval Checklist

Before approving, verify:

- [ ] **Agent Identity**: Is this the expected agent?
- [ ] **Action Scope**: Are the parameters reasonable?
- [ ] **Timing**: Is this action expected now?
- [ ] **Risk Level**: Check budget usage and recent activity
- [ ] **Business Context**: Does this align with known activities?

## Approving a Request

1. Review the request details
2. Add optional notes for the audit trail
3. Click **Approve**

The action will be executed immediately and the result recorded.

### CLI Approval

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/appr-xyz789/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Reviewed deployment plan, approved for production rollout"
  }'
```

## Denying a Request

1. Review the request details
2. Enter a reason (required)
3. Add optional notes
4. Click **Deny**

The agent will receive the denial with your reason.

### CLI Denial

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/appr-xyz789/deny \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Not approved during code freeze",
    "notes": "Code freeze in effect until Dec 20"
  }'
```

## Bulk Actions

### Bulk Approve

Select multiple pending approvals and click **Bulk Approve**:

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/bulk-approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_ids": ["appr-001", "appr-002", "appr-003"],
    "notes": "Batch approved after security review"
  }'
```

### Bulk Deny

Select multiple pending approvals and click **Bulk Deny**:

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/bulk-deny \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "approval_ids": ["appr-004", "appr-005"],
    "reason": "End of day cleanup"
  }'
```

## Expiry Handling

Approvals expire after 24 hours (configurable). Expired approvals:

- Are marked with `expired` status
- Do not execute the action
- Are logged in the audit trail

### Preventing Expiry

- Set up notifications for aging approvals
- Review pending approvals at start and end of day
- Consider shorter expiry for critical actions

## Approval Statistics

View approval metrics in **Approvals → Stats**:

- Total by status (pending, approved, denied, expired)
- Average response time
- Breakdown by agent
- Breakdown by reason code

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/approvals/stats?from=2024-12-01" \
  -H "Authorization: Bearer $TOKEN"
```

## Best Practices

!!! tip "Document Your Decisions"
    Always add notes explaining why you approved or denied. This helps with audits.

!!! tip "Check the Full Context"
    Review the policy trace and risk snapshot before deciding.

!!! warning "Never Auto-Approve"
    Don't create automation that auto-approves escalated requests. The escalation exists for a reason.

!!! tip "Set Up Alerts"
    Configure notifications for new approvals and approaching expiry.

## Related

- [Approval Workflow](../concepts/approvals.md) - Workflow concepts
- [API: Approvals](../api/approvals.md) - API reference
- [Audit](audit.md) - Viewing approval history

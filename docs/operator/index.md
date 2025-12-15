---
title: Operator Guide
description: Day-to-day operations and management
---

# Operator Guide

This guide covers day-to-day operations for teams managing UAPK Gateway.

## Overview

Operators are responsible for:

- **Approval Management**: Reviewing and acting on escalated requests
- **Agent Oversight**: Monitoring agent activity and health
- **Audit & Compliance**: Verifying logs and generating reports
- **Incident Response**: Handling security events and anomalies

## Dashboard Access

Access the operator dashboard at:

```
http://localhost:8000/ui
```

Login with your operator credentials to access:

<div class="grid cards" markdown>

-   :material-check-circle: **Approvals**

    ---

    Review and act on pending approval requests

    [:octicons-arrow-right-24: Approvals](approvals.md)

-   :material-clipboard-list: **Audit Logs**

    ---

    View activity logs and verify chain integrity

    [:octicons-arrow-right-24: Audit](audit.md)

-   :material-view-dashboard: **Dashboard**

    ---

    Monitor agent activity and system health

    [:octicons-arrow-right-24: Dashboard](dashboard.md)

-   :material-alert: **Incidents**

    ---

    Respond to security events and anomalies

    [:octicons-arrow-right-24: Incidents](incidents.md)

</div>

## Quick Actions

### Check Pending Approvals

```bash
curl "http://localhost:8000/api/v1/orgs/$ORG_ID/approvals?status=pending" \
  -H "Authorization: Bearer $TOKEN"
```

### Verify Log Chain

```bash
curl http://localhost:8000/api/v1/orgs/$ORG_ID/logs/verify/my-agent \
  -H "Authorization: Bearer $TOKEN"
```

### Suspend an Agent

```bash
curl -X POST http://localhost:8000/api/v1/orgs/$ORG_ID/manifests/$MANIFEST_ID/suspend \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Security review required"}'
```

## Operator Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access, user management, settings |
| `operator` | Approve/deny, view logs, manage agents |
| `viewer` | Read-only access to logs and status |

## Daily Checklist

- [ ] Review pending approvals
- [ ] Check for expired approvals
- [ ] Verify log chain integrity
- [ ] Review denied actions for patterns
- [ ] Check agent health metrics

## Related

- [API: Approvals](../api/approvals.md) - Approvals API
- [API: Logs](../api/logs.md) - Logs API
- [Security](../security/index.md) - Security practices

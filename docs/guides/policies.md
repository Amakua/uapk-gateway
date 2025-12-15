# Policy Configuration

How to define and manage policies in UAPK Gateway.

## Policy Structure

Policies define rules for agent actions:

```yaml
name: limit-email-sending
description: Restrict email sending rate and recipients
version: 1
enabled: true

scope:
  organizations: ["*"]
  teams: ["support"]
  agents: ["*"]
  actions: ["email:send"]

rules:
  - type: rate_limit
    max: 10
    period: 1h

  - type: parameter_validation
    parameters:
      to:
        pattern: ".*@(acme\\.com|partner\\.com)$"
        message: "Can only send to acme.com or partner.com"

  - type: require_approval
    when:
      recipients_count: ">5"
    approvers: ["support-lead"]
```

## Rule Types

### Rate Limiting

```yaml
- type: rate_limit
  max: 100
  period: 1h  # 1h, 1d, 1w
  scope: per_agent  # or per_organization
```

### Budget Limits

```yaml
- type: budget_limit
  max_cost: 100.00
  currency: USD
  period: 1d
```

### Parameter Validation

```yaml
- type: parameter_validation
  parameters:
    amount:
      max: 1000
      message: "Amount cannot exceed $1000"
```

### Time Restrictions

```yaml
- type: time_restriction
  allowed_hours:
    start: "09:00"
    end: "17:00"
  timezone: "America/New_York"
  allowed_days: ["mon", "tue", "wed", "thu", "fri"]
```

### Human Approval

```yaml
- type: require_approval
  when:
    action: "payment:send"
    amount: ">500"
  approvers: ["finance-team"]
  timeout: 24h
  auto_deny_on_timeout: true
```

## Policy Evaluation

Policies are evaluated in order:

1. Most specific scope first (agent > team > org)
2. All matching policies must pass
3. First denial stops evaluation

## Examples

### Restrict to Business Hours

```yaml
name: business-hours-only
scope:
  actions: ["*"]
rules:
  - type: time_restriction
    allowed_hours:
      start: "08:00"
      end: "18:00"
    timezone: "UTC"
```

### Limit API Costs

```yaml
name: api-cost-limit
scope:
  actions: ["openai:*", "anthropic:*"]
rules:
  - type: budget_limit
    max_cost: 50.00
    period: 1d
    scope: per_agent
```

### Require Approval for Deletions

```yaml
name: approval-for-delete
scope:
  actions: ["*:delete"]
rules:
  - type: require_approval
    approvers: ["admin"]
```

---
title: Pricing
description: Transparent, usage-based pricing
---

# Pricing

Simple, transparent pricing that scales with your usage.

<div class="pricing-grid" markdown>

<div class="pricing-card" markdown>

### Free

**$0**/month

Perfect for evaluation and small projects

- 3 agents
- 10,000 actions/month
- 30-day audit retention
- Basic approval workflows
- Community support
- Email notifications

[Get Started](../quickstart.md){ .md-button }

</div>

<div class="pricing-card featured" markdown>

### Pro

**$99**/month

For growing teams with production workloads

- 25 agents
- 100,000 actions/month
- 1-year audit retention
- Advanced approval workflows
- Email support (24h response)
- Slack integration
- Custom policies
- API access

[Start Free Trial](#){ .md-button .md-button--primary }

</div>

<div class="pricing-card" markdown>

### Enterprise

**Custom**

For organizations with advanced requirements

- Unlimited agents
- Unlimited actions
- Custom retention
- Custom workflows
- Dedicated support
- 99.99% SLA
- SSO/SAML
- On-premise option
- Audit exports
- Custom integrations

[Contact Sales](mailto:sales@uapk.dev){ .md-button }

</div>

</div>

## Plan Comparison

| Feature | Free | Pro | Enterprise |
|---------|:----:|:---:|:----------:|
| **Agents** | 3 | 25 | Unlimited |
| **Actions/month** | 10,000 | 100,000 | Unlimited |
| **Audit retention** | 30 days | 1 year | Custom |
| **Approval workflows** | Basic | Advanced | Custom |
| **Policy rules** | 10 | 100 | Unlimited |
| **API rate limit** | 60/min | 600/min | Unlimited |
| **Users** | 3 | 20 | Unlimited |
| | | | |
| **Integrations** | | | |
| Email notifications | :material-check: | :material-check: | :material-check: |
| Slack | :material-close: | :material-check: | :material-check: |
| Webhooks | :material-close: | :material-check: | :material-check: |
| SIEM export | :material-close: | :material-close: | :material-check: |
| | | | |
| **Security** | | | |
| Ed25519 signatures | :material-check: | :material-check: | :material-check: |
| Hash-chained logs | :material-check: | :material-check: | :material-check: |
| SSO/SAML | :material-close: | :material-close: | :material-check: |
| IP allowlisting | :material-close: | :material-check: | :material-check: |
| Dedicated tenant | :material-close: | :material-close: | :material-check: |
| | | | |
| **Support** | | | |
| Community forum | :material-check: | :material-check: | :material-check: |
| Email support | :material-close: | 24h response | 4h response |
| Phone support | :material-close: | :material-close: | :material-check: |
| Dedicated CSM | :material-close: | :material-close: | :material-check: |
| SLA | - | 99.9% | 99.99% |

## Usage-Based Pricing

### Actions

An "action" is a single evaluate or execute request to the gateway.

| Volume | Price per 1,000 |
|--------|-----------------|
| First 10,000 | Included |
| 10,001 - 100,000 | $1.00 |
| 100,001 - 1,000,000 | $0.50 |
| 1,000,000+ | $0.25 |

### Storage

Audit log storage beyond plan limits:

| Duration | Price per GB/month |
|----------|-------------------|
| Active (< 90 days) | $0.10 |
| Archive (> 90 days) | $0.03 |

## FAQ

??? question "What counts as an action?"
    Every call to `/gateway/execute` or `/gateway/evaluate` counts as one action. Approval decisions and log queries do not count.

??? question "What happens if I exceed my limits?"
    Free tier: Requests are rate-limited. Pro tier: Overage billed at usage rates. Enterprise: Custom arrangements.

??? question "Can I downgrade my plan?"
    Yes, you can downgrade at any time. Downgrade takes effect at the next billing cycle.

??? question "Is there a free trial for Pro?"
    Yes, Pro includes a 14-day free trial with full features. No credit card required.

??? question "What payment methods are accepted?"
    Credit cards (Visa, Mastercard, Amex) and ACH for annual plans. Enterprise customers can pay by invoice.

??? question "Are there annual discounts?"
    Yes, annual plans receive a 20% discount. Enterprise plans are typically annual.

## Self-Hosted Option

For organizations that need to run UAPK Gateway in their own infrastructure:

| Option | Description | Pricing |
|--------|-------------|---------|
| Community Edition | Free, open-source | Free |
| Enterprise License | Full features + support | Contact sales |

[View Deployment Guide](../deployment/index.md){ .md-button }

## Contact Sales

For Enterprise pricing, custom requirements, or volume discounts:

- Email: [sales@uapk.dev](mailto:sales@uapk.dev)
- Schedule a call: [Book Demo](#)

## Related

- [Pilot Program](pilot.md) - Guided implementation
- [Support](support.md) - Support options
- [Quickstart](../quickstart.md) - Get started

---
title: Roadmap
description: What's coming in UAPK Gateway
---

# Roadmap

**Last updated:** 2025-12-28

Our public roadmap for UAPK Gateway. We prioritize based on customer feedback and market needs.

## Current Version: v0.1

The current release includes core functionality:

- :material-check: Manifest registration and lifecycle
- :material-check: Policy engine (allow/deny/escalate)
- :material-check: Approval workflows
- :material-check: Hash-chained audit logs
- :material-check: Ed25519 signatures
- :material-check: REST API
- :material-check: Basic dashboard

## In Development

### v0.2 - Enhanced Workflows

*Target: 2026 H1*

| Feature | Description | Status |
|---------|-------------|--------|
| Webhook notifications | Real-time approval notifications | :material-progress-clock: In progress |
| Slack integration | Approve/deny from Slack | :material-progress-clock: In progress |
| Bulk approvals | Approve multiple requests | :material-check: Complete |
| Approval delegation | Delegate approvals to others | :material-pencil: Planned |
| Custom approval forms | Add fields to approval UI | :material-pencil: Planned |

### v0.3 - Advanced Policy

*Target: 2026 H1*

| Feature | Description | Status |
|---------|-------------|--------|
| Time-based policies | Business hours restrictions | :material-pencil: Planned |
| Geographic policies | Jurisdiction-based rules | :material-pencil: Planned |
| Counterparty management | Blocklists and allowlists | :material-pencil: Planned |
| Policy templates | Pre-built policy sets | :material-pencil: Planned |
| Policy testing | Dry-run policy changes | :material-pencil: Planned |

## Planned Features

### 2026 H2

#### Analytics & Reporting

- Usage dashboards
- Trend analysis
- Anomaly detection
- Custom reports
- Scheduled exports

#### Integrations

- PagerDuty integration
- Jira integration
- ServiceNow integration
- Custom webhooks

### 2026 H2

#### Enterprise Features

- SSO/SAML support
- SCIM provisioning
- Audit log streaming
- SIEM integration
- Role customization

#### Multi-Agent Workflows

- Agent-to-agent communication
- Workflow orchestration
- Dependency tracking
- Transaction management

## Future Considerations

These features are being evaluated based on customer feedback:

### Advanced AI Controls

| Feature | Description |
|---------|-------------|
| Prompt logging | Log prompts that led to actions |
| Output validation | Validate action results |
| Chain-of-thought | Log reasoning traces |
| Model tracking | Track which model made decisions |

### Compliance Automation

| Feature | Description |
|---------|-------------|
| SOC 2 reports | Automated evidence collection |
| GDPR tools | Data subject request handling |
| Compliance dashboard | Real-time compliance status |
| Audit preparation | Pre-audit checklists |

### Developer Experience

| Feature | Description |
|---------|-------------|
| Python SDK | Native Python client |
| TypeScript SDK | Native TypeScript client |
| CLI improvements | Enhanced command-line tools |
| Local development | Improved dev experience |

## How We Prioritize

We prioritize features based on:

1. **Customer impact**: How many customers need this?
2. **Strategic alignment**: Does it fit our vision?
3. **Technical feasibility**: Can we build it well?
4. **Market timing**: Is now the right time?

## Request a Feature

Have an idea? We'd love to hear it!

- **GitHub**: [Open a feature request](https://github.com/UAPK/gateway/issues/new)
- **Email**: [features@uapk.info](mailto:features@uapk.info)
- **Enterprise**: Contact your Customer Success Manager

## Stay Updated

- **Changelog**: [github.com/UAPK/gateway/releases](https://github.com/UAPK/gateway/releases)
- **Blog**: [blog.uapk.info](https://blog.uapk.info)
- **Twitter**: [@uapkdev](https://twitter.com/uapkdev)
- **Newsletter**: [Subscribe](#)

## Release Schedule

| Version | Target | Theme |
|---------|--------|-------|
| v0.2 | 2026 H1 | Enhanced Workflows |
| v0.3 | 2026 H1 | Advanced Policy |
| v0.4 | 2026 H2 | Analytics & Integrations |
| v1.0 | 2026 (date TBD) | Enterprise Ready |

!!! info "Dates are Estimates"
    Release dates are targets and may change based on development progress and customer feedback.

## Contributing

UAPK Gateway is open source. Contributions are welcome!

- [Contributing Guide](https://github.com/UAPK/gateway/blob/main/CONTRIBUTING.md)
- [Development Setup](https://github.com/UAPK/gateway/blob/main/docs/development.md)
- [Good First Issues](https://github.com/UAPK/gateway/labels/good%20first%20issue)

## Related

- [Quickstart](quickstart.md) - Get started now
- [Pricing](business/pricing.md) - Plan options
- [Support](business/support.md) - Get help

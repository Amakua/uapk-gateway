---
title: Pricing & Engagement
description: Open-source foundation with commercial pilots and enterprise support
---

# Pricing & Engagement

UAPK Gateway offers flexible engagement options: self-host the open-source version for free, or get expert help through commercial pilots and enterprise support.

---

## Open Source (Free)

UAPK Gateway is **Apache-2.0 licensed** and fully self-hostable.

**What you get:**
- Full source code on [GitHub](https://github.com/UAPK/gateway)
- All core features (policy enforcement, approvals, audit logs, capability tokens)
- Docker Compose deployment for one-VM setup
- Community support via [GitHub Discussions](https://github.com/UAPK/gateway/discussions)
- Complete documentation and examples
- 47ers template library

**Best for:** Teams who want to self-manage, contribute back to the project, or evaluate before engaging commercially.

**License:** [Apache License 2.0](https://github.com/UAPK/gateway/blob/main/LICENSE)

[Get Started →](../quickstart.md){ .md-button .md-button--primary }
[View on GitHub →](https://github.com/UAPK/gateway){ .md-button }

---

## Commercial Offerings

<div class="pricing-grid" markdown>

<div class="pricing-card featured" markdown>

### 1. Agent Governance Pilot

**$15,000 - $25,000** (fixed fee)

**Duration:** 2-4 weeks from kickoff to production

Implement UAPK Gateway for **one high-value workflow** and deliver a production-ready deployment.

**Includes:**
- Production-ready manifest + guardrails
- Self-hosted gateway on your infrastructure
- Integrated agent(s) via API or SDK
- Approval workflows (web UI + API)
- Evidence-grade audit logs with verified chain
- Compliance export bundle (sample)
- Operator training (2-hour session)
- 30 days post-pilot bug fixes

**Deliverables:**
- Running UAPK Gateway instance
- Active UAPK Manifest (validated and activated)
- Operator runbook and documentation
- Production deployment checklist

**Best for:** Teams who want fast results with expert guidance. Go from "compliance won't sign off" to "deployed in production" in 2-4 weeks.

[Learn More →](pilot.md){ .md-button .md-button--pilot }
[Contact Us →](mailto:mail@uapk.info){ .md-button }

</div>

<div class="pricing-card" markdown>

### 2. UAPK Blueprint Package

**$5,000 - $10,000** (design-first)

**Duration:** 1-2 weeks

For teams who want the governance design before building.

**Deliverables:**
- Agent roles, actions, and tools mapped
- Policy manifest + escalation thresholds
- Budget and risk hook design
- Integration architecture document
- Template UAPK Manifests
- Implementation roadmap

**Best for:** Teams who need to get stakeholder buy-in, plan architecture, or understand requirements before implementation.

**Next step:** Use the blueprint to self-implement, or transition to a full pilot.

[Contact Us →](mailto:mail@uapk.info){ .md-button }

</div>

<div class="pricing-card" markdown>

### 3. Enterprise Support

**Custom pricing** (recurring)

**Duration:** Ongoing (monthly or annual contracts)

For production deployments requiring dedicated support and custom development.

**Includes:**
- Custom connectors (Salesforce, M365, Slack, internal APIs)
- Compliance export tuning (SOC2, GDPR, industry-specific)
- SLA (4-hour response, 99.9% uptime commitment)
- Version upgrades and security patches
- Dedicated support channel
- Priority bug fixes and feature requests

**Best for:** Production deployments at scale, regulated environments, or teams needing ongoing vendor support.

**Typical engagement:** $3K-$10K/month depending on scale and custom requirements.

[Contact Us →](mailto:mail@uapk.info){ .md-button }

</div>

</div>

---

## Pricing Philosophy

We believe in **transparent, value-based pricing**:

1. **Open-source core** - No vendor lock-in, no hidden costs
2. **Productized pilots** - Fixed-fee, fast time-to-value, no hourly billing
3. **Enterprise support** - Recurring revenue for ongoing value, not upfront licenses

**Why this works:**
- **For you:** Predictable costs, clear ROI, fast procurement
- **For us:** Sustainable business model, aligned incentives, customer success

---

## Pilot vs. Blueprint vs. Support

| | **Pilot** | **Blueprint** | **Support** |
|---|:---:|:---:|:---:|
| **Deliverable** | Working deployment | Design document | Ongoing service |
| **Timeline** | 2-4 weeks | 1-2 weeks | Recurring |
| **Outcome** | Production-ready | Implementation plan | Maintained deployment |
| **Best for** | Fast deployment | Planning & buy-in | Long-term production |
| **Price** | $15K-$25K | $5K-$10K | $3K-$10K/month |

---

## FAQ

??? question "Is the open-source version feature-complete?"
    Yes. The Apache-2.0 version includes all core features: policy enforcement, capability tokens, approvals, tamper-evident logs, operator UI, and the 47ers library. Commercial offerings provide expertise and support, not locked features.

??? question "What's included in the pilot pricing?"
    Fixed-fee pilot pricing includes everything listed in the "Agent Governance Pilot" section above. No hidden costs. Additional agents or workflows beyond the initial scope may require a change order.

??? question "Can we self-host after a pilot?"
    Yes. Pilots deploy UAPK Gateway to **your** infrastructure. You own the deployment. After the pilot, you can self-manage (open-source) or transition to enterprise support.

??? question "What if the pilot doesn't meet objectives?"
    We work closely to ensure success. If the pilot doesn't meet agreed objectives, there's no obligation to continue. Our goal is your success, not billable hours.

??? question "Do you offer hosted/SaaS deployment?"
    Not currently. UAPK Gateway is designed for self-hosted deployment to ensure you own your data, evidence, and compliance posture. We can help with infrastructure setup as part of a pilot.

??? question "Can we start with open-source and upgrade later?"
    Absolutely. Many customers start with self-hosted open-source to evaluate, then engage for a pilot when ready to deploy in production.

??? question "What payment methods do you accept?"
    Pilots: ACH, wire transfer, or credit card (invoiced). Support contracts: Monthly or annual invoicing. We can accommodate most procurement processes.

??? question "Do you offer discounts for multiple pilots?"
    Yes. Contact us for volume pricing if you have multiple workflows or business units that need governance.

---

## Self-Hosted Deployment

The open-source version can be deployed in minutes:

```bash
# Clone and start
git clone https://github.com/UAPK/gateway.git
cd gateway
make dev

# Set up database
make migrate
make bootstrap

# Open dashboard
open http://localhost:8000
```

See the [Deployment Guide](../deployment/index.md) for production setup (Docker Compose, Caddy, backups, monitoring).

---

## Contact & Next Steps

Ready to get started?

1. **Self-Host:** Follow the [Quickstart Guide](../quickstart.md)
2. **Pilot Program:** Read the [Pilot Overview](pilot.md) and contact us
3. **Blueprint:** Email us your use case and team size
4. **Enterprise Support:** Contact us for a support contract proposal

**Email:** [mail@uapk.info](mailto:mail@uapk.info)

**Response time:** 24 hours for commercial inquiries

---

## Related

- [Pilot Program Details](pilot.md) - Full pilot SOW and deliverables
- [Enterprise Overview](index.md) - Use cases and customer stories
- [Support Options](support.md) - Support tiers and SLA details
- [Quickstart Guide](../quickstart.md) - Get started with open-source

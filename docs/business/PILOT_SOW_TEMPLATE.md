# Agent Governance Pilot - Statement of Work (Template)

**One-page SOW for fast procurement**

---

## Project Overview

**Client:** [Company Name]
**Vendor:** UAPK Gateway Team
**Project:** Agent Governance Pilot
**Duration:** 2-4 weeks from kickoff
**Fee:** $15,000 - $25,000 (fixed price)

---

## Objective

Implement UAPK Gateway to govern **[1-3 specific AI agents]** for **[use case: e.g., customer onboarding, claims triage, legal workflow]** with production-ready policy enforcement, human approvals, and tamper-evident audit logs.

---

## Scope of Work

### Phase 1: Discovery & Design (Week 1)

**Activities:**
- Requirements workshop (2-3 hours)
- Map agent roles, actions, and tools
- Define policy rules and escalation thresholds
- Design approval workflows
- Document compliance requirements (e.g., SOC2, GDPR, internal audit)

**Deliverables:**
1. UAPK Manifest (draft) - defines agent boundaries, policies, budgets
2. Integration architecture document
3. Success criteria and acceptance tests

---

### Phase 2: Implementation (Week 2-3)

**Activities:**
- Deploy UAPK Gateway to client infrastructure (self-hosted VM or cloud)
- Configure authentication (JWT + API keys)
- Integrate target agent(s) via API or SDK
- Implement connectors (e.g., HTTP, webhook, custom tools)
- Configure approval workflows (web UI + API)
- Set up tamper-evident logging with hash chaining
- Deploy to staging environment

**Deliverables:**
1. Running UAPK Gateway instance (staging)
2. Integrated agent(s) calling `/v1/gateway/evaluate` and `/v1/gateway/execute`
3. Active UAPK Manifest (validated and activated)
4. Approval workflow (UI + API)
5. Interaction logs with verified chain integrity

---

### Phase 3: Validation & Handoff (Week 3-4)

**Activities:**
- End-to-end testing (happy path + edge cases)
- Security review (secrets, API keys, connector allowlists)
- Performance validation (latency, throughput)
- Operator training (2-hour session)
- Documentation review (runbooks, troubleshooting)
- Production deployment planning

**Deliverables:**
1. Test results and performance benchmarks
2. Compliance export bundle (sample audit log export)
3. Operator runbook (how to approve/deny actions, export logs, verify chain)
4. Production deployment checklist
5. Transition to support (if applicable)

---

## Client Responsibilities

Client agrees to provide:
- Access to target AI agent(s) and integration endpoints
- Infrastructure for UAPK Gateway deployment (1 VM: 2 vCPU, 4GB RAM, PostgreSQL)
- Subject matter experts for requirements and testing (2-4 hours/week)
- Approval workflow stakeholders (for training and UAT)
- Timely feedback on deliverables

---

## Vendor Responsibilities

UAPK Gateway Team agrees to provide:
- Dedicated solutions engineer (primary contact)
- Weekly sync calls (30-60 minutes)
- Implementation of UAPK Gateway for agreed scope
- Operator training (2-hour session)
- Post-pilot support (30 days bug fixes for pilot deliverables)

---

## Success Criteria

Pilot is considered successful when:
- ✅ Target agent(s) integrated and calling gateway APIs
- ✅ UAPK Manifest active with policy enforcement (ALLOW/DENY/ESCALATE)
- ✅ Approval workflow tested and operational
- ✅ Tamper-evident logs verified (chain integrity check passes)
- ✅ Compliance export bundle generated and reviewed
- ✅ Operators trained and able to manage approvals
- ✅ Production deployment plan approved

---

## Pricing & Payment Terms

**Fixed Fee:** $[15,000 - $25,000] (based on complexity and agent count)

**Payment Schedule:**
- 50% upon SOW signature (project kickoff)
- 50% upon successful completion and acceptance

**Included:**
- All deliverables listed above
- Solutions engineering time
- Operator training (2 hours)
- 30 days post-pilot bug fixes

**Not Included (optional add-ons):**
- Custom connectors beyond HTTP/webhook (priced separately)
- Extended training (beyond 2 hours)
- Ongoing support after 30-day period (see Enterprise Support)
- Compliance consulting (e.g., SOC2 audit prep)

---

## Timeline

| Week | Phase | Key Milestones |
|------|-------|----------------|
| 1 | Discovery | Requirements, manifest design, architecture |
| 2 | Implementation | Gateway deployed, agents integrated, staging live |
| 3 | Validation | Testing, training, compliance export |
| 4 | Handoff | Production deployment, runbook, support transition |

**Start Date:** [Date]
**Target Go-Live:** [Date + 4 weeks]

---

## Assumptions & Constraints

- Pilot covers **1-3 AI agents** (additional agents priced separately)
- Pilot covers **1-2 approval workflows** (additional workflows may extend timeline)
- Client provides infrastructure (VM + database)
- Gateway deployed **self-hosted** on client infrastructure
- Standard connectors (HTTP, webhook) included; custom connectors are add-ons
- Pilot does not include multi-gateway federation or cross-org workflows (v0.2+)

---

## Post-Pilot Transition

### Option 1: Production Support (Recommended)
Transition to Enterprise Support contract:
- SLA: 4-hour response, 99.9% uptime commitment
- Ongoing updates and security patches
- Custom connector development
- Compliance export tuning
- Pricing: [Contact for quote based on scale]

### Option 2: Self-Managed
Client maintains UAPK Gateway independently:
- Open-source license (Apache-2.0)
- Community support via GitHub
- No SLA or dedicated support
- Client responsible for updates and security

---

## Terms & Conditions

- **Acceptance:** Deliverables accepted within 5 business days or deemed accepted
- **Change Requests:** Additional agents, connectors, or workflows require change order
- **Confidentiality:** Both parties agree to NDA (if applicable)
- **IP Ownership:** Client owns UAPK Manifest and configuration; vendor retains core platform IP
- **Warranty:** 30-day bug fix warranty on pilot deliverables
- **Liability:** Limited to fees paid (see standard MSA or pilot agreement)

---

## Approval & Signature

**Client:**

Signature: ____________________
Name: ____________________
Title: ____________________
Date: ____________________

**Vendor (UAPK Gateway Team):**

Signature: ____________________
Name: ____________________
Title: ____________________
Date: ____________________

---

## Contact & Project Management

**Client Project Manager:**
Name: ____________________
Email: ____________________
Phone: ____________________

**Vendor Solutions Engineer:**
Name: ____________________
Email: ____________________
Phone: ____________________

**Escalation Contact (Vendor):**
Email: `pilots@uapk.info` or see `SECURITY.md`

---

## Appendix A: Example Use Cases

This template is used for pilots in:
- **Legal:** Settlement negotiation agent, takedown notice agent
- **Finance:** KYC onboarding agent, trading execution agent
- **Compliance:** Vendor due diligence agent, risk screening agent
- **Customer Support:** Refund approval agent, escalation triage agent

See `examples/47ers/` for reference manifests.

---

**Last Updated:** 2025-12-15
**Template Version:** 1.0

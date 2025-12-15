"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import (
    actions,
    api_keys,
    approvals,
    auth,
    capabilities,
    capability_tokens,
    gateway,
    health,
    interaction_records,
    logs,
    manifests,
    memberships,
    metrics,
    organizations,
    policies,
    users,
)

router = APIRouter(prefix="/v1")

# Include routers
router.include_router(health.router, tags=["Health"])
router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(users.router)
router.include_router(memberships.router)
router.include_router(api_keys.router)

# UAPK core routes
router.include_router(actions.router)
router.include_router(manifests.router)
router.include_router(policies.router)
router.include_router(capability_tokens.router)
router.include_router(capabilities.router)
router.include_router(interaction_records.router)
router.include_router(logs.router)

# Agent Interaction Gateway
router.include_router(gateway.router)

# Approval workflow
router.include_router(approvals.router)

# Metrics
router.include_router(metrics.router)

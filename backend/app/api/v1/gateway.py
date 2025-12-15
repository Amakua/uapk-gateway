"""Gateway API endpoints - evaluate and execute agent actions."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import ApiKeyAuth, DbSession
from app.gateway.service import GatewayService
from app.schemas.gateway import (
    GatewayActionRequest,
    GatewayDecisionResponse,
    GatewayExecuteResponse,
)

router = APIRouter(prefix="/gateway", tags=["Gateway"])


@router.post("/evaluate", response_model=GatewayDecisionResponse)
async def evaluate_action(
    request: GatewayActionRequest,
    db: DbSession,
    api_key: ApiKeyAuth,
) -> GatewayDecisionResponse:
    """Evaluate an agent action request without executing.

    Returns the policy decision (ALLOW, DENY, ESCALATE) and reasons.

    **Authentication:**
    - Requires API key via X-API-Key header
    - Organization is derived from the API key

    **Use Case:**
    - Pre-flight checks before executing an action
    - Agents can check if an action would be allowed without side effects

    **Response:**
    - `decision`: ALLOW, DENY, or ESCALATE
    - `reasons`: List of reason codes explaining the decision
    - `approval_id`: If ESCALATE, the ID of the approval task
    """
    gateway = GatewayService(db)
    return await gateway.evaluate(
        org_id=api_key.org_id,
        request=request,
    )


@router.post("/execute", response_model=GatewayExecuteResponse)
async def execute_action(
    request: GatewayActionRequest,
    db: DbSession,
    api_key: ApiKeyAuth,
) -> GatewayExecuteResponse:
    """Evaluate and execute an agent action request.

    If ALLOW: Executes the tool connector and returns the result.
    If DENY: Returns the decision without executing.
    If ESCALATE: Creates an approval task and returns the approval_id.

    **Authentication:**
    - Requires API key via X-API-Key header
    - Organization is derived from the API key

    **Flow:**
    1. Validate manifest exists and is active
    2. Evaluate policies (action type, tool, amounts, jurisdiction, counterparty, budget)
    3. If ALLOW: Execute tool via configured connector, increment budget
    4. If DENY: Return decision
    5. If ESCALATE: Create approval task for human review
    6. Log interaction record for audit

    **Response:**
    - `decision`: ALLOW, DENY, or ESCALATE
    - `executed`: Whether the tool was actually executed
    - `result`: Tool result (if executed)
    - `approval_id`: If ESCALATE, the ID of the approval task
    """
    gateway = GatewayService(db)
    return await gateway.execute(
        org_id=api_key.org_id,
        request=request,
    )

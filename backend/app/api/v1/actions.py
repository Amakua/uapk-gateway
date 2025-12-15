"""Action gateway API endpoint - the core of UAPK.

This is where agents POST action requests. The gateway evaluates policies,
enforces capabilities and budgets, and logs tamper-evident interaction records.
"""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from app.api.deps import DbSession
from app.schemas.action import ActionRequest, ActionResponse
from app.services.action_gateway import ActionGatewayService

router = APIRouter(prefix="/actions", tags=["Actions"])


@router.post("", response_model=ActionResponse)
async def submit_action(
    request: ActionRequest,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> ActionResponse:
    """Submit an action request for policy evaluation.

    This is the core gateway endpoint. Agents authenticate with a capability token
    JWT in the Authorization header and submit action requests. The gateway:

    1. Validates the capability token
    2. Checks the action is within granted capabilities
    3. Evaluates applicable policies
    4. Creates a tamper-evident interaction record
    5. Returns the decision (approved, denied, or pending)

    **Authentication:**
    - Bearer token with a capability token JWT
    - Example: `Authorization: Bearer <capability_token_jwt>`

    **Response decisions:**
    - `approved`: Action is allowed, proceed with execution
    - `denied`: Action is blocked by policy or capability limits
    - `pending`: Action requires human approval before proceeding
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_token = parts[1]

    gateway = ActionGatewayService(db)
    return await gateway.process_action(jwt_token, request)

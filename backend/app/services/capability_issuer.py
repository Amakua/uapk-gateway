"""Service layer for capability issuers and token issuance."""

import secrets
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.capability_jwt import (
    CapabilityTokenClaims,
    TokenConstraints,
    create_capability_token,
)
from app.core.ed25519 import get_gateway_key_manager, public_key_from_base64
from app.core.logging import get_logger
from app.models.capability_issuer import CapabilityIssuer, IssuerStatus
from app.schemas.capability_issuer import (
    IssueTokenRequest,
    IssueTokenResponse,
    IssuerCreate,
    IssuerResponse,
)

logger = get_logger("services.capability_issuer")


class CapabilityIssuerError(Exception):
    """Raised when capability issuer operations fail."""

    pass


async def register_issuer(
    db: AsyncSession,
    org_id: UUID,
    issuer_data: IssuerCreate,
    user_id: UUID | None = None,
) -> IssuerResponse:
    """Register a new capability issuer with public key.

    Args:
        db: Database session
        org_id: Organization ID
        issuer_data: Issuer registration data
        user_id: Optional user ID who created the issuer

    Returns:
        Created issuer response

    Raises:
        CapabilityIssuerError: If registration fails
    """
    # Validate public key format
    try:
        public_key_from_base64(issuer_data.public_key)
    except Exception as e:
        raise CapabilityIssuerError(f"Invalid public key format: {e}")

    # Check for existing issuer with same issuer_id
    existing = await db.execute(
        select(CapabilityIssuer).where(
            CapabilityIssuer.org_id == org_id,
            CapabilityIssuer.issuer_id == issuer_data.issuer_id,
        )
    )
    if existing.scalar_one_or_none():
        raise CapabilityIssuerError(
            f"Issuer with ID '{issuer_data.issuer_id}' already exists"
        )

    issuer = CapabilityIssuer(
        org_id=org_id,
        issuer_id=issuer_data.issuer_id,
        name=issuer_data.name,
        public_key=issuer_data.public_key,
        description=issuer_data.description,
        status=IssuerStatus.ACTIVE,
        created_by_user_id=user_id,
    )

    db.add(issuer)
    await db.commit()
    await db.refresh(issuer)

    logger.info(
        "capability_issuer_registered",
        org_id=str(org_id),
        issuer_id=issuer_data.issuer_id,
        created_by=str(user_id) if user_id else None,
    )

    return IssuerResponse.model_validate(issuer)


async def get_issuer(
    db: AsyncSession,
    org_id: UUID,
    issuer_id: str,
) -> IssuerResponse | None:
    """Get a capability issuer by ID.

    Args:
        db: Database session
        org_id: Organization ID
        issuer_id: Issuer identifier

    Returns:
        Issuer response or None if not found
    """
    result = await db.execute(
        select(CapabilityIssuer).where(
            CapabilityIssuer.org_id == org_id,
            CapabilityIssuer.issuer_id == issuer_id,
        )
    )
    issuer = result.scalar_one_or_none()
    if issuer:
        return IssuerResponse.model_validate(issuer)
    return None


async def list_issuers(
    db: AsyncSession,
    org_id: UUID,
    include_revoked: bool = False,
) -> list[IssuerResponse]:
    """List capability issuers for an organization.

    Args:
        db: Database session
        org_id: Organization ID
        include_revoked: Whether to include revoked issuers

    Returns:
        List of issuer responses
    """
    query = select(CapabilityIssuer).where(CapabilityIssuer.org_id == org_id)

    if not include_revoked:
        query = query.where(CapabilityIssuer.status == IssuerStatus.ACTIVE)

    query = query.order_by(CapabilityIssuer.created_at.desc())

    result = await db.execute(query)
    issuers = result.scalars().all()

    return [IssuerResponse.model_validate(issuer) for issuer in issuers]


async def revoke_issuer(
    db: AsyncSession,
    org_id: UUID,
    issuer_id: str,
) -> IssuerResponse:
    """Revoke a capability issuer.

    Args:
        db: Database session
        org_id: Organization ID
        issuer_id: Issuer identifier

    Returns:
        Updated issuer response

    Raises:
        CapabilityIssuerError: If issuer not found or already revoked
    """
    from datetime import UTC, datetime

    result = await db.execute(
        select(CapabilityIssuer).where(
            CapabilityIssuer.org_id == org_id,
            CapabilityIssuer.issuer_id == issuer_id,
        )
    )
    issuer = result.scalar_one_or_none()

    if not issuer:
        raise CapabilityIssuerError(f"Issuer '{issuer_id}' not found")

    if issuer.status == IssuerStatus.REVOKED:
        raise CapabilityIssuerError(f"Issuer '{issuer_id}' is already revoked")

    issuer.status = IssuerStatus.REVOKED
    issuer.revoked_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(issuer)

    logger.info(
        "capability_issuer_revoked",
        org_id=str(org_id),
        issuer_id=issuer_id,
    )

    return IssuerResponse.model_validate(issuer)


async def issue_capability_token(
    db: AsyncSession,
    org_id: UUID,
    request: IssueTokenRequest,
    issuer_id: str = "gateway",
) -> IssueTokenResponse:
    """Issue a capability token for an agent.

    Args:
        db: Database session
        org_id: Organization ID
        request: Token issuance request
        issuer_id: ID of the issuer (defaults to gateway)

    Returns:
        Issued token response

    Raises:
        CapabilityIssuerError: If token issuance fails
    """
    from datetime import UTC, datetime

    # If not gateway, verify issuer exists and is active
    if issuer_id != "gateway":
        result = await db.execute(
            select(CapabilityIssuer).where(
                CapabilityIssuer.org_id == org_id,
                CapabilityIssuer.issuer_id == issuer_id,
                CapabilityIssuer.status == IssuerStatus.ACTIVE,
            )
        )
        issuer = result.scalar_one_or_none()
        if not issuer:
            raise CapabilityIssuerError(
                f"Active issuer '{issuer_id}' not found"
            )

    now = int(time.time())
    token_id = f"cap-{secrets.token_hex(16)}"

    # Build constraints if provided
    constraints = None
    if request.constraints:
        constraints = TokenConstraints(
            amount_max=request.constraints.amount_max,
            jurisdictions=request.constraints.jurisdictions,
            counterparty_allowlist=request.constraints.counterparty_allowlist,
            counterparty_denylist=request.constraints.counterparty_denylist,
            expires_at=request.constraints.expires_at,
        )

    claims = CapabilityTokenClaims(
        iss=issuer_id,
        sub=request.agent_id,
        org_id=str(org_id),
        uapk_id=request.uapk_id,
        allowed_action_types=request.allowed_action_types,
        allowed_tools=request.allowed_tools,
        constraints=constraints,
        delegation_depth=request.delegation_depth,
        iat=now,
        exp=now + request.expires_in_seconds,
        jti=token_id,
    )

    # Sign with gateway key (for now, all tokens signed by gateway)
    token = create_capability_token(claims)

    issued_at = datetime.fromtimestamp(now, tz=UTC)
    expires_at = datetime.fromtimestamp(now + request.expires_in_seconds, tz=UTC)

    logger.info(
        "capability_token_issued",
        org_id=str(org_id),
        issuer_id=issuer_id,
        agent_id=request.agent_id,
        uapk_id=request.uapk_id,
        token_id=token_id,
        expires_at=expires_at.isoformat(),
    )

    # Build constraints dict for response
    constraints_dict = None
    if request.constraints:
        constraints_dict = {}
        if request.constraints.amount_max is not None:
            constraints_dict["amount_max"] = request.constraints.amount_max
        if request.constraints.jurisdictions:
            constraints_dict["jurisdictions"] = request.constraints.jurisdictions
        if request.constraints.counterparty_allowlist:
            constraints_dict["counterparty_allowlist"] = (
                request.constraints.counterparty_allowlist
            )
        if request.constraints.counterparty_denylist:
            constraints_dict["counterparty_denylist"] = (
                request.constraints.counterparty_denylist
            )
        if request.constraints.expires_at:
            constraints_dict["expires_at"] = request.constraints.expires_at.isoformat()

    return IssueTokenResponse(
        token=token,
        token_id=token_id,
        issuer_id=issuer_id,
        agent_id=request.agent_id,
        uapk_id=request.uapk_id,
        org_id=str(org_id),
        issued_at=issued_at,
        expires_at=expires_at,
        allowed_action_types=request.allowed_action_types,
        allowed_tools=request.allowed_tools,
        constraints=constraints_dict,
    )


async def get_gateway_public_key() -> tuple[str, str]:
    """Get the gateway's public key for token verification.

    Returns:
        Tuple of (issuer_id, base64_public_key)
    """
    key_manager = get_gateway_key_manager()
    return "gateway", key_manager.get_public_key_base64()


async def get_issuer_public_keys(
    db: AsyncSession,
    org_id: UUID,
) -> dict[str, str]:
    """Get all active issuer public keys for an organization.

    Args:
        db: Database session
        org_id: Organization ID

    Returns:
        Dict of issuer_id -> base64_public_key
    """
    result = await db.execute(
        select(CapabilityIssuer).where(
            CapabilityIssuer.org_id == org_id,
            CapabilityIssuer.status == IssuerStatus.ACTIVE,
        )
    )
    issuers = result.scalars().all()

    keys = {issuer.issuer_id: issuer.public_key for issuer in issuers}

    # Always include gateway key
    gateway_id, gateway_key = await get_gateway_public_key()
    keys[gateway_id] = gateway_key

    return keys

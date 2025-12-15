"""API dependencies for dependency injection."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.api_key import ApiKey
from app.models.membership import MembershipRole
from app.models.user import User
from app.services.api_key import ApiKeyService
from app.services.auth import AuthService
from app.services.membership import MembershipService

# Type alias for settings dependency
SettingsDep = Annotated[Settings, Depends(get_settings)]

# Type alias for database session dependency
DbSession = Annotated[AsyncSession, Depends(get_db)]

# HTTP Bearer token security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    """Get the current authenticated user from JWT token.

    Raises HTTPException if not authenticated.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(UUID(user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# Type alias for current user dependency
CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_user_optional(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User | None:
    """Get the current user if authenticated, None otherwise."""
    if credentials is None:
        return None

    try:
        return await get_current_user(db, credentials)
    except HTTPException:
        return None


CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]


async def get_api_key_auth(
    db: DbSession,
    settings: SettingsDep,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> ApiKey:
    """Authenticate via API key header.

    Raises HTTPException if not authenticated.
    """
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    api_key_service = ApiKeyService(db)
    api_key = await api_key_service.authenticate_api_key(x_api_key)

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    return api_key


# Type alias for API key auth dependency
ApiKeyAuth = Annotated[ApiKey, Depends(get_api_key_auth)]


def require_org_role(required_roles: list[MembershipRole]):
    """Factory for dependency that checks user has required role in organization.

    Usage:
        @router.post("/orgs/{org_id}/something")
        async def do_something(
            org_id: UUID,
            _: Annotated[None, Depends(require_org_role([MembershipRole.ADMIN, MembershipRole.OWNER]))],
            user: CurrentUser,
            db: DbSession,
        ):
            ...
    """

    async def check_role(
        org_id: UUID,
        user: CurrentUser,
        db: DbSession,
    ) -> None:
        membership_service = MembershipService(db)
        has_role = await membership_service.user_has_role(org_id, user.id, required_roles)

        if not has_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this organization",
            )

    return check_role


# Common role check dependencies
RequireOrgAdmin = Depends(require_org_role([MembershipRole.OWNER, MembershipRole.ADMIN]))
RequireOrgOperator = Depends(
    require_org_role([MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.OPERATOR])
)
RequireOrgViewer = Depends(
    require_org_role(
        [MembershipRole.OWNER, MembershipRole.ADMIN, MembershipRole.OPERATOR, MembershipRole.VIEWER]
    )
)

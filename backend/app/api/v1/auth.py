"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import LoginRequest, TokenResponse, UserWithOrgsResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: DbSession,
) -> TokenResponse:
    """Authenticate with email and password.

    Returns a JWT access token on success.
    """
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(data.email, data.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return await auth_service.create_token_for_user(user)


@router.get("/me", response_model=UserWithOrgsResponse)
async def get_current_user_info(
    user: CurrentUser,
    db: DbSession,
) -> UserWithOrgsResponse:
    """Get current authenticated user's information.

    Includes organization memberships.
    """
    auth_service = AuthService(db)
    user_with_orgs = await auth_service.get_user_with_orgs(user.id)

    if user_with_orgs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user_with_orgs

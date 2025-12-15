"""User API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import UserCreate, UserList, UserResponse
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    _user: CurrentUser,  # Require authentication
    db: DbSession,
) -> UserResponse:
    """Create a new user.

    Requires authentication. In a real system, this might require admin privileges.
    """
    user_service = UserService(db)

    # Check if email already exists
    if await user_service.email_exists(data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{data.email}' already exists",
        )

    user = await user_service.create_user(data)
    return UserResponse.model_validate(user)


@router.get("", response_model=UserList)
async def list_users(
    _user: CurrentUser,  # Require authentication
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> UserList:
    """List all users.

    Requires authentication. In a real system, this might be restricted.
    """
    user_service = UserService(db)
    return await user_service.list_users(limit=limit, offset=offset)

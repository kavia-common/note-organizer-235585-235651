from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.core.auth import create_access_token, hash_password, verify_password, get_current_user
from src.api.core.db import get_db
from src.api.models import User
from src.api.schemas import ApiMessage, LoginRequest, RegisterRequest, TokenResponse, UserMeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a user account and returns an access token.",
    operation_id="register_user",
)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a new user and return a JWT access token."""
    existing = db.execute(select(User).where(User.email == str(req.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=str(req.email),
        password_hash=hash_password(req.password),
        display_name=req.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, email=user.email)
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Validates credentials and returns an access token.",
    operation_id="login_user",
)
def login(req: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Login using email + password and return a JWT access token."""
    user = db.execute(select(User).where(User.email == str(req.email))).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user_id=user.id, email=user.email)
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Get current user",
    description="Returns the authenticated user's profile.",
    operation_id="get_current_user_profile",
)
def me(user: User = Depends(get_current_user)) -> UserMeResponse:
    """Return the current authenticated user's profile."""
    return UserMeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/logout",
    response_model=ApiMessage,
    summary="Logout",
    description="Stateless JWT logout; client should delete its token.",
    operation_id="logout_user",
)
def logout() -> ApiMessage:
    """JWT is stateless; logout is implemented client-side by deleting the token."""
    return ApiMessage(message="Logged out (client should discard token).")

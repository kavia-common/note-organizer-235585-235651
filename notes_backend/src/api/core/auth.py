from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.api.core.config import get_settings
from src.api.core.db import get_db
from src.api.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
settings = get_settings()


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its stored hash."""
    return pwd_context.verify(password, password_hash)


# PUBLIC_INTERFACE
def create_access_token(*, user_id: UUID, email: str) -> str:
    """Create a signed JWT access token for the user."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_exp_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


# PUBLIC_INTERFACE
def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency to retrieve the current user from the Authorization: Bearer <token> header.
    """
    if creds is None or not creds.credentials:
        raise _unauthorized()

    token = creds.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as e:
        raise _unauthorized("Token expired") from e
    except jwt.PyJWTError as e:
        raise _unauthorized("Invalid token") from e

    sub = payload.get("sub")
    if not sub:
        raise _unauthorized("Invalid token payload")

    try:
        user_id = UUID(str(sub))
    except ValueError as e:
        raise _unauthorized("Invalid token subject") from e

    user = db.get(User, user_id)
    if not user:
        raise _unauthorized("User not found")

    return user

from datetime import datetime, timedelta
from typing import Optional, Annotated
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .config import settings
from .database import get_db

# Use Argon2 for password hashing (more secure, no 72-byte limit)
# Support both argon2 and bcrypt for migration from bcrypt to argon2
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],  # Try argon2 first, fallback to bcrypt for migration
    deprecated="auto",
    argon2__memory_cost=65536,  # 64 MB memory cost
    argon2__time_cost=3,  # 3 iterations
    argon2__parallelism=4,  # 4 parallel threads
    bcrypt__ident="2b",  # Use bcrypt 2b identifier for legacy hashes
    bcrypt__rounds=12,  # Standard rounds
)
security = HTTPBearer()


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    tenant_id: Optional[int] = None,
):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "type": "access"})

    # Add tenant_id to token if provided
    if tenant_id is not None:
        to_encode.update({"tenant_id": tenant_id})

    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def create_refresh_token(data: dict, tenant_id: Optional[int] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})

    # Add tenant_id to token if provided
    if tenant_id is not None:
        to_encode.update({"tenant_id": tenant_id})

    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    Supports both Argon2 (new) and bcrypt (legacy) for migration.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using Argon2 (no length limit).
    Always uses Argon2 for new passwords.
    """
    return pwd_context.hash(password)


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a password hash needs to be rehashed.
    Returns True if hash is bcrypt (legacy) and should be migrated to Argon2.
    """
    try:
        # Check if hash starts with bcrypt identifier ($2a$, $2b$, $2y$)
        if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            return True
        # Argon2 hashes start with $argon2
        return False
    except (AttributeError, TypeError):
        return False


def verify_token(token: str, token_type: str = "access") -> dict:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db),
):
    from ..models.user import User

    # Import here to avoid circular imports
    try:
        from .tenant import tenant_service
    except ImportError:
        tenant_service = None

    token = credentials.credentials
    payload = verify_token(token, "access")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    # Get tenant_id from token if available
    tenant_id = payload.get("tenant_id")

    # Build query
    query = select(User).where(User.id == int(user_id))

    # Add tenant filter if tenant_id is available
    if tenant_id is not None and hasattr(User, "tenant_id"):
        query = query.where(User.tenant_id == tenant_id)

    # Execute query
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    # Set tenant context if tenant_service is available
    if tenant_service and hasattr(user, "tenant_id") and user.tenant_id:
        tenant_service.set_tenant_id(user.tenant_id)

    return user

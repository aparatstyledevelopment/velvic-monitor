from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.errors import AuthError

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
_ALGO = "HS256"


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _pwd.verify(password, hashed)


def create_access_token(*, user_id: UUID, org_id: UUID, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=settings.jwt_access_ttl_seconds)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def create_refresh_token(*, user_id: UUID, org_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=settings.jwt_refresh_ttl_seconds)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGO])
    except JWTError as e:
        raise AuthError("invalid or expired token") from e

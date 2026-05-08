from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import AuthError

_BCRYPT_ROUNDS = 12
_ALGO = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=_BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


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

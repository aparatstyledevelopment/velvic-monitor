from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AppUser, Org
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.core.errors import AuthError, ConflictError, NotFoundError


async def signup(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    org_name: str,
    display_name: str | None = None,
) -> tuple[AppUser, Org, str, str]:
    existing = await session.scalar(select(AppUser).where(AppUser.email == email))
    if existing is not None:
        raise ConflictError("email already registered")

    org = Org(name=org_name)
    session.add(org)
    await session.flush()

    user = AppUser(
        org_id=org.id,
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        role="admin",
    )
    session.add(user)
    await session.flush()

    access = create_access_token(user_id=user.id, org_id=org.id, role=user.role)
    refresh = create_refresh_token(user_id=user.id, org_id=org.id)
    return user, org, access, refresh


async def login(
    session: AsyncSession, *, email: str, password: str
) -> tuple[AppUser, str, str]:
    user = await session.scalar(select(AppUser).where(AppUser.email == email))
    if user is None:
        raise AuthError("invalid credentials")
    if user.locked_until is not None and user.locked_until > datetime.now(UTC):
        raise AuthError("account locked, contact admin")
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        await session.flush()
        raise AuthError("invalid credentials")

    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(UTC)
    await session.flush()

    access = create_access_token(user_id=user.id, org_id=user.org_id, role=user.role)
    refresh = create_refresh_token(user_id=user.id, org_id=user.org_id)
    return user, access, refresh


async def get_user(session: AsyncSession, user_id: UUID) -> AppUser:
    user = await session.get(AppUser, user_id)
    if user is None:
        raise NotFoundError("user not found")
    return user

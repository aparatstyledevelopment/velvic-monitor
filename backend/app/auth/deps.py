from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AppUser
from app.auth.security import decode_token
from app.auth.service import get_user
from app.core.db import get_session
from app.core.errors import AuthError
from app.tenancy.middleware import set_org_scope


async def current_user(
    access_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[AppUser]:
    if access_token is None:
        raise AuthError("not authenticated")
    payload = decode_token(access_token)
    if payload.get("type") != "access":
        raise AuthError("wrong token type")
    user_id = UUID(payload["sub"])
    org_id = UUID(payload["org_id"])
    await set_org_scope(session, org_id)
    user = await get_user(session, user_id)
    yield user

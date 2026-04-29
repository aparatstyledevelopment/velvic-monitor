from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.auth import LoginRequest, MeResponse, SignupRequest
from app.auth.deps import current_user
from app.auth.models import AppUser, Org
from app.auth.service import login, signup
from app.core.config import get_settings
from app.core.db import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, *, access: str, refresh: str) -> None:
    settings = get_settings()
    secure = settings.env != "local"
    response.set_cookie(
        "access_token",
        access,
        max_age=settings.jwt_access_ttl_seconds,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        max_age=settings.jwt_refresh_ttl_seconds,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/api/auth",
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup_route(
    body: SignupRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    user, _, access, refresh = await signup(
        session,
        email=body.email,
        password=body.password,
        org_name=body.org_name,
        display_name=body.display_name,
    )
    await session.commit()
    _set_auth_cookies(response, access=access, refresh=refresh)
    return {"user_id": str(user.id)}


@router.post("/login")
async def login_route(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    user, access, refresh = await login(
        session, email=body.email, password=body.password
    )
    await session.commit()
    _set_auth_cookies(response, access=access, refresh=refresh)
    return {"user_id": str(user.id)}


@router.post("/logout")
async def logout_route(response: Response) -> dict[str, bool]:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
async def me_route(
    user: AppUser = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    org = await session.get(Org, user.org_id)
    assert org is not None
    return MeResponse(
        user_id=user.id,
        org_id=user.org_id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        org_name=org.name,
    )

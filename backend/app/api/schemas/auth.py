from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    org_name: str = Field(min_length=1, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class MeResponse(BaseModel):
    user_id: UUID
    org_id: UUID
    email: EmailStr
    display_name: str | None
    role: str
    org_name: str

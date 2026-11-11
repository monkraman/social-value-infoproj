from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator

from app.core.security import validate_password_strength

Role = Literal["superadmin", "bid_author", "reviewer"]


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    # Least privilege by default; only a superadmin can create users (see /auth/register).
    role: Role = "bid_author"

    @model_validator(mode="after")
    def _strong_password(self):
        validate_password_strength(self.password, email=str(self.email), name=self.name)
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=128)


class PasswordChange(BaseModel):
    current_password: str = Field(..., max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from models.users_models import AuthProviderType, UserRole
from uuid import UUID

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: str
    full_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    disabled: bool = False
    picture: str | None = None
    role: UserRole | None = None

class UserUpdate(BaseModel):
    full_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None

class UserSocialAccountBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
    provider: AuthProviderType
    provider_id: str
    is_verified: bool | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    email: str | None = None
    picture: str | None = None

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    social_accounts: list[UserSocialAccountBase] | None = None
    model_config = ConfigDict(from_attributes=True)

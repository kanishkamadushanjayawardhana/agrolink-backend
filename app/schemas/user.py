
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.FARMER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=150)
    farm_name: str | None = Field(default=None, max_length=150)
    company_name: str | None = Field(default=None, max_length=150)
    profile_image: str | None = Field(default=None, max_length=500)


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    phone: str | None = None
    location: str | None = None
    farm_name: str | None = None
    company_name: str | None = None
    profile_image: str | None = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str

from pydantic import BaseModel, EmailStr

from src.modules.identity_access.models import Role


class PasswordHash(BaseModel):
    value: str


class Permission(BaseModel):
    key: str


class RoleEntity(BaseModel):
    role: Role
    permissions: list[Permission]


class UserAggregate(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    password_hash: PasswordHash

"""Modelos de contrato (Pydantic) para users-service."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

UserRole = Literal["admin", "employee"]


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=100, examples=["Ana López"])
    email: EmailStr = Field(..., examples=["ana.lopez@nexosalas.com"])
    department: str = Field(..., min_length=2, max_length=60, examples=["Ingeniería"])
    password: str = Field(..., min_length=6, max_length=72, examples=["ClaveSegura123"])
    role: UserRole = Field(default="employee")


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=100)
    department: str | None = Field(default=None, min_length=2, max_length=60)
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    department: str
    role: UserRole
    is_active: bool
    created_at: str
    updated_at: str


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["admin@nexosalas.com"])
    password: str = Field(..., min_length=6, max_length=72, examples=["Admin123!"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

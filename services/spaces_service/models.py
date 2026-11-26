"""Modelos de contrato (Pydantic) para spaces-service."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SpaceStatus = Literal["available", "maintenance"]


class SpaceCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=20, examples=["SALA-A1"])
    name: str = Field(..., min_length=3, max_length=100, examples=["Sala Innovación Norte"])
    building: str = Field(..., min_length=2, max_length=60, examples=["Edificio Central"])
    floor: int = Field(..., ge=0, le=100, examples=[2])
    capacity: int = Field(..., ge=1, le=500, examples=[12])
    resources: list[str] = Field(
        default_factory=list,
        examples=[["Proyector 4K", "Pizarra inteligente", "Videoconferencia"]],
    )
    status: SpaceStatus = Field(default="available")
    description: str = Field(default="", max_length=300)


class SpaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=100)
    building: str | None = Field(default=None, min_length=2, max_length=60)
    floor: int | None = Field(default=None, ge=0, le=100)
    capacity: int | None = Field(default=None, ge=1, le=500)
    resources: list[str] | None = None
    status: SpaceStatus | None = None
    description: str | None = Field(default=None, max_length=300)


class SpaceResponse(BaseModel):
    id: int
    code: str
    name: str
    building: str
    floor: int
    capacity: int
    resources: list[str]
    status: SpaceStatus
    description: str
    created_at: str
    updated_at: str


class SpaceValidationResponse(BaseModel):
    valid: bool
    reason: str
    space: SpaceResponse

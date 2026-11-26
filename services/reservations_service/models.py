"""Modelos de contrato (Pydantic) y validaciones para reservations-service."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ReservationStatus = Literal["CONFIRMED", "CANCELLED"]
TIME_REGEX = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class ReservationCreate(BaseModel):
    user_id: int | None = Field(
        default=None,
        ge=1,
        description="ID del usuario (si se omite, se toma del token JWT actual).",
    )
    space_id: int = Field(..., ge=1, examples=[1])
    title: str = Field(..., min_length=3, max_length=120, examples=["Revisión trimestral SOA"])
    reservation_date: str = Field(..., examples=["2026-12-01"])
    start_time: str = Field(..., examples=["10:00"])
    end_time: str = Field(..., examples=["11:30"])
    attendees: int = Field(..., ge=1, le=500, examples=[8])
    notes: str = Field(default="", max_length=300)

    @field_validator("reservation_date")
    @classmethod
    def validate_date_format(cls, value: str) -> str:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("La fecha debe tener formato ISO YYYY-MM-DD.") from exc
        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, value: str) -> str:
        if not TIME_REGEX.match(value):
            raise ValueError("La hora debe tener formato 24h HH:MM (ej. 09:30).")
        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> "ReservationCreate":
        if self.end_time <= self.start_time:
            raise ValueError("La hora de fin (end_time) debe ser posterior a start_time.")
        return self


class ReservationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    reservation_date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    attendees: int | None = Field(default=None, ge=1, le=500)
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("reservation_date")
    @classmethod
    def validate_date_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("La fecha debe tener formato ISO YYYY-MM-DD.") from exc
        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not TIME_REGEX.match(value):
            raise ValueError("La hora debe tener formato 24h HH:MM.")
        return value


class SoaStepTrace(BaseModel):
    service: str
    operation: str
    status: str
    detail: str


class ReservationResponse(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: str
    space_id: int
    space_code: str
    space_name: str
    title: str
    reservation_date: str
    start_time: str
    end_time: str
    attendees: int
    notes: str
    status: ReservationStatus
    confirmation_code: str
    created_at: str
    updated_at: str
    soa_trace: list[SoaStepTrace] = Field(default_factory=list)

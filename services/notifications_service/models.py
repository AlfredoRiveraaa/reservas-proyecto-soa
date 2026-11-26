"""Modelos de contrato (Pydantic) para notifications-service."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

NotificationEventType = Literal[
    "RESERVATION_CONFIRMED",
    "RESERVATION_UPDATED",
    "RESERVATION_CANCELLED",
]
NotificationChannel = Literal["EMAIL", "IN_APP"]
NotificationStatus = Literal["SENT", "READ", "FAILED"]


class NotificationCreate(BaseModel):
    reservation_id: int = Field(..., ge=1)
    user_id: int = Field(..., ge=1)
    recipient_email: EmailStr
    recipient_name: str = Field(..., min_length=2, max_length=100)
    event_type: NotificationEventType = Field(default="RESERVATION_CONFIRMED")
    subject: str = Field(..., min_length=3, max_length=160)
    message: str = Field(..., min_length=5, max_length=1000)
    channel: NotificationChannel = Field(default="EMAIL")


class NotificationStatusUpdate(BaseModel):
    status: NotificationStatus


class NotificationResponse(BaseModel):
    id: int
    confirmation_code: str
    reservation_id: int
    user_id: int
    recipient_email: str
    recipient_name: str
    event_type: NotificationEventType
    subject: str
    message: str
    channel: NotificationChannel
    status: NotificationStatus
    created_at: str
    updated_at: str

"""Aplicación FastAPI del Servicio de Notificaciones y Confirmaciones (notifications-service)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from services.notifications_service.database import NotificationsDatabase
from services.notifications_service.models import (
    NotificationCreate,
    NotificationEventType,
    NotificationResponse,
    NotificationStatusUpdate,
)
from services.notifications_service.repository import NotificationRepository
from shared.errors import register_error_handlers
from shared.security import get_current_user, get_user_or_internal_service, require_admin

SERVICE_NAME = "notifications-service"
SERVICE_VERSION = "1.0.0"


def create_app(db_path: Path | None = None) -> FastAPI:
    """Fábrica de la aplicación FastAPI para notifications-service."""
    app = FastAPI(
        title="ReservaSOA — Servicio de Notificaciones y Confirmaciones",
        description=(
            "Servicio SOA independiente que emite folios de confirmación y registra "
            "el historial de notificaciones de reservaciones."
        ),
        version=SERVICE_VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app, SERVICE_NAME)

    db = NotificationsDatabase(db_path=db_path)
    repo = NotificationRepository(db)
    app.state.db = db
    app.state.repo = repo

    @app.get("/health", tags=["Salud"])
    def health_check() -> dict[str, str]:
        return {"service": SERVICE_NAME, "version": SERVICE_VERSION, "status": "ok"}

    @app.post(
        "/notifications",
        response_model=NotificationResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Notificaciones"],
    )
    def create_notification(
        payload: NotificationCreate,
        _: dict[str, Any] = Depends(get_user_or_internal_service),
    ) -> NotificationResponse:
        return repo.create(payload)

    @app.get("/notifications", response_model=list[NotificationResponse], tags=["Notificaciones"])
    def list_notifications(
        user_id: int | None = Query(default=None, ge=1),
        reservation_id: int | None = Query(default=None, ge=1),
        event_type: NotificationEventType | None = Query(default=None),
        _: dict[str, Any] = Depends(get_user_or_internal_service),
    ) -> list[NotificationResponse]:
        return repo.list_all(
            user_id=user_id,
            reservation_id=reservation_id,
            event_type=event_type,
        )

    @app.get(
        "/notifications/{notification_id}",
        response_model=NotificationResponse,
        tags=["Notificaciones"],
    )
    def get_notification(
        notification_id: int,
        _: dict[str, Any] = Depends(get_user_or_internal_service),
    ) -> NotificationResponse:
        return repo.get_by_id(notification_id)

    @app.patch(
        "/notifications/{notification_id}/status",
        response_model=NotificationResponse,
        tags=["Notificaciones"],
    )
    def update_notification_status(
        notification_id: int,
        payload: NotificationStatusUpdate,
        _: dict[str, Any] = Depends(get_current_user),
    ) -> NotificationResponse:
        return repo.update_status(notification_id, payload.status)

    @app.delete(
        "/notifications/{notification_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Notificaciones"],
    )
    def delete_notification(
        notification_id: int,
        _: dict[str, Any] = Depends(require_admin),
    ) -> Response:
        repo.delete(notification_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = create_app()

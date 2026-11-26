"""Aplicación FastAPI del Servicio de Reservaciones y Orquestación (reservations-service)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from services.reservations_service.database import ReservationsDatabase
from services.reservations_service.models import (
    ReservationCreate,
    ReservationResponse,
    ReservationStatus,
    ReservationUpdate,
)
from services.reservations_service.orchestrator import ReservationOrchestrator
from services.reservations_service.repository import ReservationRepository
from shared.config import get_settings
from shared.errors import ForbiddenError, register_error_handlers
from shared.http_client import ServiceHttpClient
from shared.security import get_current_user, require_admin

SERVICE_NAME = "reservations-service"
SERVICE_VERSION = "1.0.0"


def create_app(
    db_path: Path | None = None,
    users_client: ServiceHttpClient | None = None,
    spaces_client: ServiceHttpClient | None = None,
    notifications_client: ServiceHttpClient | None = None,
) -> FastAPI:
    """Fábrica de la aplicación FastAPI para reservations-service."""
    settings = get_settings()
    app = FastAPI(
        title="ReservaSOA — Servicio de Reservaciones y Orquestación",
        description=(
            "Servicio SOA orquestador que gestiona el ciclo de vida de reservaciones, "
            "valida horarios y coordina vía HTTP a users-service, spaces-service y "
            "notifications-service."
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

    db = ReservationsDatabase(db_path=db_path)
    repo = ReservationRepository(db)
    orchestrator = ReservationOrchestrator(
        repo=repo,
        users_client=users_client
        or ServiceHttpClient("users-service", settings.users_service_url),
        spaces_client=spaces_client
        or ServiceHttpClient("spaces-service", settings.spaces_service_url),
        notifications_client=notifications_client
        or ServiceHttpClient("notifications-service", settings.notifications_service_url),
    )

    app.state.db = db
    app.state.repo = repo
    app.state.orchestrator = orchestrator

    @app.get("/health", tags=["Salud"])
    def health_check() -> dict[str, str]:
        return {"service": SERVICE_NAME, "version": SERVICE_VERSION, "status": "ok"}

    @app.get("/reservations", response_model=list[ReservationResponse], tags=["Reservaciones"])
    def list_reservations(
        user_id: int | None = Query(default=None, ge=1),
        space_id: int | None = Query(default=None, ge=1),
        reservation_date: str | None = Query(default=None),
        status_filter: ReservationStatus | None = Query(default=None, alias="status"),
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> list[ReservationResponse]:
        # Un empleado regular puede consultar la agenda general o filtrar por usuario
        _ = current_user
        return repo.list_all(
            user_id=user_id,
            space_id=space_id,
            reservation_date=reservation_date,
            status_filter=status_filter,
        )

    @app.post(
        "/reservations",
        response_model=ReservationResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Reservaciones"],
    )
    async def create_reservation(
        payload: ReservationCreate,
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> ReservationResponse:
        token_user_id = int(current_user["sub"])
        effective_user_id = payload.user_id if payload.user_id is not None else token_user_id
        if effective_user_id != token_user_id and current_user.get("role") != "admin":
            raise ForbiddenError("Solo un administrador puede reservar a nombre de otro usuario.")
        return await orchestrator.create_reservation(payload, effective_user_id)

    @app.get(
        "/reservations/{reservation_id}",
        response_model=ReservationResponse,
        tags=["Reservaciones"],
    )
    def get_reservation(
        reservation_id: int,
        _: dict[str, Any] = Depends(get_current_user),
    ) -> ReservationResponse:
        return repo.get_by_id(reservation_id)

    @app.put(
        "/reservations/{reservation_id}",
        response_model=ReservationResponse,
        tags=["Reservaciones"],
    )
    async def update_reservation(
        reservation_id: int,
        payload: ReservationUpdate,
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> ReservationResponse:
        existing = repo.get_by_id(reservation_id)
        if existing.user_id != int(current_user["sub"]) and current_user.get("role") != "admin":
            raise ForbiddenError("Solo el propietario o un administrador puede modificar la reserva.")
        return await orchestrator.update_reservation(reservation_id, payload)

    @app.post(
        "/reservations/{reservation_id}/cancel",
        response_model=ReservationResponse,
        tags=["Reservaciones"],
    )
    async def cancel_reservation(
        reservation_id: int,
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> ReservationResponse:
        existing = repo.get_by_id(reservation_id)
        if existing.user_id != int(current_user["sub"]) and current_user.get("role") != "admin":
            raise ForbiddenError("Solo el propietario o un administrador puede cancelar la reserva.")
        return await orchestrator.cancel_reservation(reservation_id)

    @app.delete(
        "/reservations/{reservation_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Reservaciones"],
    )
    def delete_reservation(
        reservation_id: int,
        _: dict[str, Any] = Depends(require_admin),
    ) -> Response:
        repo.delete(reservation_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = create_app()

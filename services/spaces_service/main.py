"""Aplicación FastAPI del Servicio de Espacios y Recursos (spaces-service)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from services.spaces_service.database import SpacesDatabase
from services.spaces_service.models import (
    SpaceCreate,
    SpaceResponse,
    SpaceStatus,
    SpaceUpdate,
    SpaceValidationResponse,
)
from services.spaces_service.repository import SpaceRepository
from shared.errors import register_error_handlers
from shared.security import get_user_or_internal_service, require_admin

SERVICE_NAME = "spaces-service"
SERVICE_VERSION = "1.0.0"


def create_app(db_path: Path | None = None) -> FastAPI:
    """Fábrica de la aplicación FastAPI para spaces-service."""
    app = FastAPI(
        title="ReservaSOA — Servicio de Espacios y Recursos",
        description=(
            "Servicio SOA independiente encargado del catálogo de salas, capacidad, "
            "equipamiento audiovisual y validación de disponibilidad operativa."
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

    db = SpacesDatabase(db_path=db_path)
    repo = SpaceRepository(db)
    app.state.db = db
    app.state.repo = repo

    @app.get("/health", tags=["Salud"])
    def health_check() -> dict[str, str]:
        return {"service": SERVICE_NAME, "version": SERVICE_VERSION, "status": "ok"}

    @app.get("/spaces", response_model=list[SpaceResponse], tags=["Espacios"])
    def list_spaces(
        status_filter: SpaceStatus | None = Query(default=None, alias="status"),
        min_capacity: int | None = Query(default=None, ge=1),
        building: str | None = Query(default=None),
        resource: str | None = Query(default=None),
    ) -> list[SpaceResponse]:
        return repo.list_all(
            status_filter=status_filter,
            min_capacity=min_capacity,
            building=building,
            resource=resource,
        )

    @app.post(
        "/spaces",
        response_model=SpaceResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Espacios"],
    )
    def create_space(
        payload: SpaceCreate,
        _: dict[str, Any] = Depends(require_admin),
    ) -> SpaceResponse:
        return repo.create(payload)

    @app.get("/spaces/{space_id}", response_model=SpaceResponse, tags=["Espacios"])
    def get_space(space_id: int) -> SpaceResponse:
        return repo.get_by_id(space_id)

    @app.get(
        "/spaces/{space_id}/validate",
        response_model=SpaceValidationResponse,
        tags=["Validación SOA"],
    )
    def validate_space_for_booking(
        space_id: int,
        attendees: int = Query(..., ge=1, description="Número de asistentes requeridos"),
        _: dict[str, Any] = Depends(get_user_or_internal_service),
    ) -> SpaceValidationResponse:
        space = repo.get_by_id(space_id)
        if space.status != "available":
            return SpaceValidationResponse(
                valid=False,
                reason=f"La sala '{space.name}' se encuentra en estado '{space.status}'.",
                space=space,
            )
        if attendees > space.capacity:
            return SpaceValidationResponse(
                valid=False,
                reason=(
                    f"La cantidad de asistentes ({attendees}) excede la capacidad "
                    f"máxima de la sala ({space.capacity})."
                ),
                space=space,
            )
        return SpaceValidationResponse(
            valid=True,
            reason="Espacio disponible y con capacidad suficiente.",
            space=space,
        )

    @app.put("/spaces/{space_id}", response_model=SpaceResponse, tags=["Espacios"])
    def update_space(
        space_id: int,
        payload: SpaceUpdate,
        _: dict[str, Any] = Depends(require_admin),
    ) -> SpaceResponse:
        return repo.update(space_id, payload)

    @app.delete(
        "/spaces/{space_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Espacios"],
    )
    def delete_space(
        space_id: int,
        _: dict[str, Any] = Depends(require_admin),
    ) -> Response:
        repo.delete(space_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = create_app()

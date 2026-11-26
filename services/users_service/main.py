"""Aplicación FastAPI del Servicio de Usuarios y Autenticación (users-service)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from services.users_service.database import UsersDatabase
from services.users_service.models import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from services.users_service.repository import UserRepository
from shared.errors import ForbiddenError, UnauthorizedError, register_error_handlers
from shared.security import (
    create_access_token,
    get_current_user,
    get_user_or_internal_service,
    require_admin,
    verify_password,
)

SERVICE_NAME = "users-service"
SERVICE_VERSION = "1.0.0"


def create_app(db_path: Path | None = None) -> FastAPI:
    """Fábrica de la aplicación FastAPI para users-service."""
    app = FastAPI(
        title="ReservaSOA — Servicio de Usuarios y Autenticación",
        description=(
            "Servicio SOA independiente responsable del ciclo de vida de usuarios, "
            "roles corporativos y emisión/verificación de tokens JWT."
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

    db = UsersDatabase(db_path=db_path)
    repo = UserRepository(db)
    app.state.db = db
    app.state.repo = repo

    @app.get("/health", tags=["Salud"])
    def health_check() -> dict[str, str]:
        return {"service": SERVICE_NAME, "version": SERVICE_VERSION, "status": "ok"}

    @app.post(
        "/auth/register",
        response_model=UserResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Autenticación"],
    )
    def register_user(payload: UserCreate) -> UserResponse:
        return repo.create(payload)

    @app.post("/auth/login", response_model=TokenResponse, tags=["Autenticación"])
    def login(payload: LoginRequest) -> TokenResponse:
        record = repo.get_auth_record_by_email(payload.email)
        if record is None or not verify_password(payload.password, record["password_hash"]):
            raise UnauthorizedError("Correo electrónico o contraseña incorrectos.")
        if not bool(record["is_active"]):
            raise ForbiddenError("La cuenta de usuario se encuentra desactivada.")

        user = repo.get_by_id(int(record["id"]))
        token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
            }
        )
        return TokenResponse(access_token=token, user=user)

    @app.get("/auth/me", response_model=UserResponse, tags=["Autenticación"])
    def get_me(current_user: dict[str, Any] = Depends(get_current_user)) -> UserResponse:
        return repo.get_by_id(int(current_user["sub"]))

    @app.get("/users", response_model=list[UserResponse], tags=["Usuarios"])
    def list_users(
        only_active: bool = Query(default=False, description="Filtrar solo usuarios activos"),
        _: dict[str, Any] = Depends(get_user_or_internal_service),
    ) -> list[UserResponse]:
        return repo.list_all(only_active=only_active)

    @app.post(
        "/users",
        response_model=UserResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["Usuarios"],
    )
    def create_user(
        payload: UserCreate,
        _: dict[str, Any] = Depends(require_admin),
    ) -> UserResponse:
        return repo.create(payload)

    @app.get("/users/{user_id}", response_model=UserResponse, tags=["Usuarios"])
    def get_user(
        user_id: int,
        _: dict[str, Any] = Depends(get_user_or_internal_service),
    ) -> UserResponse:
        return repo.get_by_id(user_id)

    @app.put("/users/{user_id}", response_model=UserResponse, tags=["Usuarios"])
    def update_user(
        user_id: int,
        payload: UserUpdate,
        _: dict[str, Any] = Depends(require_admin),
    ) -> UserResponse:
        return repo.update(user_id, payload)

    @app.delete(
        "/users/{user_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Usuarios"],
    )
    def delete_user(
        user_id: int,
        _: dict[str, Any] = Depends(require_admin),
    ) -> Response:
        repo.delete(user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app


app = create_app()

"""Fixtures compartidos para pruebas unitarias, CRUD e integración SOA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.notifications_service.main import create_app as create_notifications_app
from services.reservations_service.main import create_app as create_reservations_app
from services.spaces_service.main import create_app as create_spaces_app
from services.users_service.main import create_app as create_users_app
from shared.errors import UpstreamServiceError
from shared.http_client import ServiceHttpClient


class InProcessServiceHttpClient(ServiceHttpClient):
    """Cliente HTTP real sobre httpx.ASGITransport para probar integración entre servicios."""

    def __init__(self, target_service: str, app: FastAPI, simulate_down: bool = False) -> None:
        super().__init__(target_service=target_service, base_url=f"http://{target_service}")
        self.app = app
        self.simulate_down = simulate_down

    async def request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        if self.simulate_down:
            raise UpstreamServiceError(
                message=f"No se pudo establecer comunicación con {self.target_service}.",
                status_code=503,
                error_code="UPSTREAM_UNAVAILABLE",
                details={"target_service": self.target_service},
            )
        transport = httpx.ASGITransport(app=self.app)
        async with httpx.AsyncClient(transport=transport, base_url=self.base_url) as client:
            return await client.request(
                method=method.upper(),
                url=f"/{path.lstrip('/')}",
                json=json_body,
                params=params,
                headers=self._build_headers(headers),
            )


@pytest.fixture()
def soa_env(tmp_path: Path) -> dict[str, Any]:
    """Crea una instancia aislada de los 4 servicios SOA con sus 4 BDs SQLite independientes."""
    users_app = create_users_app(db_path=tmp_path / "users.db")
    spaces_app = create_spaces_app(db_path=tmp_path / "spaces.db")
    notifications_app = create_notifications_app(db_path=tmp_path / "notifications.db")

    users_http = InProcessServiceHttpClient("users-service", users_app)
    spaces_http = InProcessServiceHttpClient("spaces-service", spaces_app)
    notifications_http = InProcessServiceHttpClient("notifications-service", notifications_app)

    reservations_app = create_reservations_app(
        db_path=tmp_path / "reservations.db",
        users_client=users_http,
        spaces_client=spaces_http,
        notifications_client=notifications_http,
    )

    users_client = TestClient(users_app)
    spaces_client = TestClient(spaces_app)
    notifications_client = TestClient(notifications_app)
    reservations_client = TestClient(reservations_app)

    # Crear usuario administrador y empleado base
    admin_resp = users_client.post(
        "/auth/register",
        json={
            "full_name": "Admin Pruebas",
            "email": "admin@nexosalas.com",
            "department": "TI",
            "password": "Admin123!",
            "role": "admin",
        },
    )
    assert admin_resp.status_code == 201
    admin_user = admin_resp.json()

    emp_resp = users_client.post(
        "/auth/register",
        json={
            "full_name": "Ana López",
            "email": "ana@nexosalas.com",
            "department": "Ingeniería",
            "password": "Ana12345",
            "role": "employee",
        },
    )
    assert emp_resp.status_code == 201
    emp_user = emp_resp.json()

    admin_token = users_client.post(
        "/auth/login",
        json={"email": "admin@nexosalas.com", "password": "Admin123!"},
    ).json()["access_token"]

    emp_token = users_client.post(
        "/auth/login",
        json={"email": "ana@nexosalas.com", "password": "Ana12345"},
    ).json()["access_token"]

    return {
        "users_client": users_client,
        "spaces_client": spaces_client,
        "notifications_client": notifications_client,
        "reservations_client": reservations_client,
        "users_http": users_http,
        "spaces_http": spaces_http,
        "notifications_http": notifications_http,
        "admin_user": admin_user,
        "emp_user": emp_user,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "emp_headers": {"Authorization": f"Bearer {emp_token}"},
    }

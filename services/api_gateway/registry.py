"""Catálogo/Registro dinámico de servicios SOA con verificación de salud en vivo."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx

from shared.config import Settings


@dataclass(frozen=True)
class ServiceDescriptor:
    name: str
    title: str
    base_url: str
    port: int
    prefix: str
    database: str
    capabilities: list[str]


class ServiceRegistry:
    """Mantiene el directorio de servicios SOA y consulta su estado operativo."""

    def __init__(self, settings: Settings) -> None:
        self.timeout = settings.http_timeout_seconds
        self.services: list[ServiceDescriptor] = [
            ServiceDescriptor(
                name="users-service",
                title="Servicio de Usuarios y Autenticación",
                base_url=settings.users_service_url,
                port=settings.users_service_port,
                prefix="/api/users, /api/auth",
                database="data/users.db",
                capabilities=["CRUD Usuarios", "Registro", "Login JWT", "Control de roles"],
            ),
            ServiceDescriptor(
                name="spaces-service",
                title="Servicio de Espacios y Recursos",
                base_url=settings.spaces_service_url,
                port=settings.spaces_service_port,
                prefix="/api/spaces",
                database="data/spaces.db",
                capabilities=[
                    "CRUD Salas",
                    "Catálogo de recursos",
                    "Filtros de capacidad",
                    "Validación operativa SOA",
                ],
            ),
            ServiceDescriptor(
                name="reservations-service",
                title="Servicio de Reservaciones y Orquestación",
                base_url=settings.reservations_service_url,
                port=settings.reservations_service_port,
                prefix="/api/reservations",
                database="data/reservations.db",
                capabilities=[
                    "CRUD Reservaciones",
                    "Detección de traslapes",
                    "Orquestación E2E HTTP",
                    "Trazabilidad SOA",
                ],
            ),
            ServiceDescriptor(
                name="notifications-service",
                title="Servicio de Notificaciones y Confirmaciones",
                base_url=settings.notifications_service_url,
                port=settings.notifications_service_port,
                prefix="/api/notifications",
                database="data/notifications.db",
                capabilities=[
                    "Emisión de folios CONF",
                    "Historial de confirmaciones",
                    "Actualización de estado",
                ],
            ),
        ]

    async def _probe_service(self, descriptor: ServiceDescriptor) -> dict[str, Any]:
        started = time.perf_counter()
        status_label = "DOWN"
        version = "unknown"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{descriptor.base_url}/health")
                if resp.status_code == 200:
                    status_label = "UP"
                    version = resp.json().get("version", "1.0.0")
        except httpx.RequestError:
            status_label = "DOWN"

        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "name": descriptor.name,
            "title": descriptor.title,
            "status": status_label,
            "version": version,
            "port": descriptor.port,
            "base_url": descriptor.base_url,
            "gateway_prefix": descriptor.prefix,
            "docs_url": f"{descriptor.base_url}/docs",
            "database": descriptor.database,
            "capabilities": descriptor.capabilities,
            "latency_ms": latency_ms,
        }

    async def get_catalog(self) -> list[dict[str, Any]]:
        results = await asyncio.gather(*(self._probe_service(svc) for svc in self.services))
        return list(results)

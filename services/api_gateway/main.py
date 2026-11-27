"""Aplicación FastAPI del API Gateway, Catálogo SOA y servidor del Cliente Web."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from services.api_gateway.registry import ServiceRegistry
from shared.config import PROJECT_ROOT, get_settings
from shared.errors import build_error_payload, register_error_handlers

SERVICE_NAME = "api-gateway"
SERVICE_VERSION = "1.1.0"
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def create_app() -> FastAPI:
    """Fábrica de la aplicación FastAPI para el API Gateway con pool HTTP persistente."""
    settings = get_settings()
    registry = ServiceRegistry(settings)

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        app_instance.state.http_client = httpx.AsyncClient(
            timeout=settings.http_timeout_seconds,
            verify=False,
            limits=httpx.Limits(max_keepalive_connections=32, max_connections=64),
        )
        try:
            yield
        finally:
            await app_instance.state.http_client.aclose()

    app = FastAPI(
        title="ReservaSOA — API Gateway y Catálogo de Servicios",
        description=(
            "Punto de entrada unificado para el cliente web y consumidores externos. "
            "Expone el catálogo dinámico de servicios SOA y enruta solicitudes HTTP/JSON."
        ),
        version=SERVICE_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app, SERVICE_NAME)

    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    route_map: dict[str, str] = {
        "auth": settings.users_service_url,
        "users": settings.users_service_url,
        "spaces": settings.spaces_service_url,
        "reservations": settings.reservations_service_url,
        "notifications": settings.notifications_service_url,
    }

    def _get_client() -> httpx.AsyncClient:
        client = getattr(app.state, "http_client", None)
        if client is None or client.is_closed:
            client = httpx.AsyncClient(
                timeout=settings.http_timeout_seconds,
                verify=False,
                limits=httpx.Limits(max_keepalive_connections=32, max_connections=64),
            )
            app.state.http_client = client
        return client

    @app.get("/", include_in_schema=False)
    def serve_frontend() -> Response:
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file, headers={"Cache-Control": "no-cache"})
        return JSONResponse({"message": "API Gateway de ReservaSOA activo. Visite /docs."})

    @app.get("/health", tags=["Salud"])
    def health_check() -> dict[str, str]:
        return {"service": SERVICE_NAME, "version": SERVICE_VERSION, "status": "ok"}

    @app.get("/registry/services", tags=["Catálogo SOA"])
    async def list_registered_services() -> dict[str, Any]:
        services = await registry.get_catalog(client=_get_client())
        up_count = sum(1 for item in services if item["status"] == "UP")
        return {
            "gateway": SERVICE_NAME,
            "total_services": len(services),
            "services_up": up_count,
            "services": services,
        }

    async def _forward(request: Request, target_base: str, upstream_path: str) -> Response:
        url = f"{target_base.rstrip('/')}/{upstream_path.lstrip('/')}"
        headers: dict[str, str] = {}
        for header_name in ("authorization", "content-type", "accept", "x-service-key"):
            if header_name in request.headers:
                headers[header_name] = request.headers[header_name]

        body = await request.body()
        try:
            client = _get_client()
            upstream = await client.request(
                method=request.method,
                url=url,
                params=dict(request.query_params),
                content=body if body else None,
                headers=headers,
            )
        except httpx.TimeoutException:
            return JSONResponse(
                status_code=504,
                content=build_error_payload(
                    SERVICE_NAME,
                    "GATEWAY_TIMEOUT",
                    f"Tiempo de espera agotado al contactar el servicio en {target_base}.",
                ),
            )
        except httpx.RequestError:
            return JSONResponse(
                status_code=503,
                content=build_error_payload(
                    SERVICE_NAME,
                    "SERVICE_UNAVAILABLE",
                    f"El servicio destino ({target_base}) no está disponible en este momento.",
                ),
            )

        content_type = upstream.headers.get("content-type", "application/json")
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type=content_type.split(";")[0],
        )

    @app.api_route(
        "/api/{resource}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        tags=["Enrutamiento SOA"],
    )
    async def proxy_root(resource: str, request: Request) -> Response:
        target = route_map.get(resource)
        if not target:
            return JSONResponse(
                status_code=404,
                content=build_error_payload(
                    SERVICE_NAME,
                    "UNKNOWN_SERVICE_ROUTE",
                    f"No existe un servicio registrado para '/api/{resource}'.",
                ),
            )
        return await _forward(request, target, resource)

    @app.api_route(
        "/api/{resource}/{subpath:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        tags=["Enrutamiento SOA"],
    )
    async def proxy_subpath(resource: str, subpath: str, request: Request) -> Response:
        target = route_map.get(resource)
        if not target:
            return JSONResponse(
                status_code=404,
                content=build_error_payload(
                    SERVICE_NAME,
                    "UNKNOWN_SERVICE_ROUTE",
                    f"No existe un servicio registrado para '/api/{resource}/{subpath}'.",
                ),
            )
        return await _forward(request, target, f"{resource}/{subpath}")

    return app


app = create_app()

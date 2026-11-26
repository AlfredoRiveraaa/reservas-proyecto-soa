"""Jerarquía de excepciones de negocio y manejadores uniformes para FastAPI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ServiceError(Exception):
    """Excepción base estructurada para todos los servicios SOA."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "SERVICE_ERROR",
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details


class NotFoundError(ServiceError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message, status_code=404, error_code="RESOURCE_NOT_FOUND", details=details)


class ConflictError(ServiceError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message, status_code=409, error_code="RESOURCE_CONFLICT", details=details)


class UnauthorizedError(ServiceError):
    def __init__(self, message: str = "Credenciales o token inválido.", details: Any = None) -> None:
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED", details=details)


class ForbiddenError(ServiceError):
    def __init__(
        self, message: str = "No tiene permisos para esta operación.", details: Any = None
    ) -> None:
        super().__init__(message, status_code=403, error_code="FORBIDDEN", details=details)


class BusinessValidationError(ServiceError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(
            message, status_code=422, error_code="BUSINESS_VALIDATION_ERROR", details=details
        )


class UpstreamServiceError(ServiceError):
    def __init__(
        self,
        message: str,
        status_code: int = 503,
        error_code: str = "UPSTREAM_SERVICE_UNAVAILABLE",
        details: Any = None,
    ) -> None:
        super().__init__(message, status_code=status_code, error_code=error_code, details=details)


def build_error_payload(
    service_name: str, error_code: str, message: str, details: Any = None
) -> dict[str, Any]:
    """Construye la respuesta estándar de error JSON de ReservaSOA."""
    return {
        "error_code": error_code,
        "message": message,
        "details": details,
        "service": service_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def register_error_handlers(app: FastAPI, service_name: str) -> None:
    """Registra manejadores globales para garantizar respuestas comprensibles y homogéneas."""

    @app.exception_handler(ServiceError)
    async def handle_service_error(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(service_name, exc.error_code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", "Valor inválido"),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=build_error_payload(
                service_name,
                "INPUT_VALIDATION_ERROR",
                "Los datos de entrada no cumplen con el contrato del servicio.",
                errors,
            ),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(
                service_name,
                f"HTTP_{exc.status_code}",
                str(exc.detail),
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=build_error_payload(
                service_name,
                "INTERNAL_SERVER_ERROR",
                "Ocurrió un error interno inesperado en el servicio.",
                {"exception": type(exc).__name__},
            ),
        )

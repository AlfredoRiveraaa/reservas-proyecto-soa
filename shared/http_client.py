"""Cliente HTTP asíncrono reutilizable para comunicación entre servicios SOA."""

from __future__ import annotations

from typing import Any

import httpx

from shared.config import get_settings
from shared.errors import UpstreamServiceError


class ServiceHttpClient:
    """Encapsula llamadas REST/HTTP entre servicios con timeout, llave interna y manejo de fallos."""

    def __init__(self, target_service: str, base_url: str, timeout: float | None = None) -> None:
        settings = get_settings()
        self.target_service = target_service
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout if timeout is not None else settings.http_timeout_seconds
        self.internal_service_key = settings.internal_service_key

    def _build_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "X-Service-Key": self.internal_service_key,
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    async def request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await client.request(
                    method=method.upper(),
                    url=url,
                    json=json_body,
                    params=params,
                    headers=self._build_headers(headers),
                )
        except httpx.TimeoutException as exc:
            raise UpstreamServiceError(
                message=f"Tiempo de espera agotado al comunicarse con {self.target_service}.",
                status_code=504,
                error_code="UPSTREAM_TIMEOUT",
                details={"target_service": self.target_service, "url": url},
            ) from exc
        except httpx.RequestError as exc:
            raise UpstreamServiceError(
                message=f"No se pudo establecer comunicación con {self.target_service}.",
                status_code=503,
                error_code="UPSTREAM_UNAVAILABLE",
                details={"target_service": self.target_service, "url": url},
            ) from exc

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await self.request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await self.request("POST", path, json_body=json_body, headers=headers)

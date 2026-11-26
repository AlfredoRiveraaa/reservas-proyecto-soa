"""Configuración centralizada cargada desde variables de entorno (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Parámetros de configuración de red, seguridad y persistencia."""

    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    internal_service_key: str

    gateway_port: int
    users_service_port: int
    spaces_service_port: int
    reservations_service_port: int
    notifications_service_port: int

    users_service_url: str
    spaces_service_url: str
    reservations_service_url: str
    notifications_service_url: str

    data_dir: Path
    http_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir_env = os.getenv("DATA_DIR", "data")
        data_path = Path(data_dir_env)
        if not data_path.is_absolute():
            data_path = PROJECT_ROOT / data_path
        data_path.mkdir(parents=True, exist_ok=True)

        return cls(
            jwt_secret_key=os.getenv(
                "JWT_SECRET_KEY", "dev-only-jwt-secret-key-reservasoa-2026"
            ),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "120")),
            internal_service_key=os.getenv(
                "INTERNAL_SERVICE_KEY", "dev-only-internal-service-key-soa"
            ),
            gateway_port=int(os.getenv("GATEWAY_PORT", "8000")),
            users_service_port=int(os.getenv("USERS_SERVICE_PORT", "8001")),
            spaces_service_port=int(os.getenv("SPACES_SERVICE_PORT", "8002")),
            reservations_service_port=int(os.getenv("RESERVATIONS_SERVICE_PORT", "8003")),
            notifications_service_port=int(os.getenv("NOTIFICATIONS_SERVICE_PORT", "8004")),
            users_service_url=os.getenv("USERS_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/"),
            spaces_service_url=os.getenv("SPACES_SERVICE_URL", "http://127.0.0.1:8002").rstrip("/"),
            reservations_service_url=os.getenv(
                "RESERVATIONS_SERVICE_URL", "http://127.0.0.1:8003"
            ).rstrip("/"),
            notifications_service_url=os.getenv(
                "NOTIFICATIONS_SERVICE_URL", "http://127.0.0.1:8004"
            ).rstrip("/"),
            data_dir=data_path,
            http_timeout_seconds=float(os.getenv("HTTP_TIMEOUT_SECONDS", "5.0")),
        )

    def db_path(self, filename: str) -> Path:
        """Devuelve la ruta de base de datos SQLite dedicada para un servicio."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / filename


def get_settings() -> Settings:
    """Obtiene la configuración actual a partir de las variables de entorno."""
    return Settings.from_env()

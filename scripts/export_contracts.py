"""Exporta los contratos OpenAPI 3.0 en formato YAML de todos los servicios SOA."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from services.api_gateway.main import create_app as create_gateway_app
from services.notifications_service.main import create_app as create_notifications_app
from services.reservations_service.main import create_app as create_reservations_app
from services.spaces_service.main import create_app as create_spaces_app
from services.users_service.main import create_app as create_users_app


def main() -> None:
    contracts_dir = ROOT_DIR / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)

    apps = {
        "users-service.openapi.yaml": create_users_app(),
        "spaces-service.openapi.yaml": create_spaces_app(),
        "reservations-service.openapi.yaml": create_reservations_app(),
        "notifications-service.openapi.yaml": create_notifications_app(),
        "api-gateway.openapi.yaml": create_gateway_app(),
    }

    for filename, app in apps.items():
        schema = app.openapi()
        out_path = contracts_dir / filename
        out_path.write_text(
            yaml.safe_dump(schema, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"Exportado contrato OpenAPI: {out_path.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()

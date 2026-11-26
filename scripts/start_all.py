"""Lanzador unificado para iniciar los 4 servicios SOA y el API Gateway en local."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from shared.config import get_settings


def main() -> None:
    settings = get_settings()
    processes: list[tuple[str, subprocess.Popen[bytes], int]] = []

    targets = [
        ("users-service", "services.users_service.main:app", settings.users_service_port),
        ("spaces-service", "services.spaces_service.main:app", settings.spaces_service_port),
        (
            "notifications-service",
            "services.notifications_service.main:app",
            settings.notifications_service_port,
        ),
        (
            "reservations-service",
            "services.reservations_service.main:app",
            settings.reservations_service_port,
        ),
        ("api-gateway", "services.api_gateway.main:app", settings.gateway_port),
    ]

    print("=" * 68)
    print("  ReservaSOA — Iniciando ecosistema de servicios SOA independientes")
    print("=" * 68)

    try:
        for name, app_path, port in targets:
            cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                app_path,
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ]
            proc = subprocess.Popen(cmd, cwd=str(ROOT_DIR))
            processes.append((name, proc, port))
            print(f"  [+] Lanzando {name:<22} -> http://127.0.0.1:{port}")

        print("\nEsperando verificación /health de todos los servicios...")
        for name, _, port in targets:
            ready = False
            for _ in range(30):
                try:
                    resp = httpx.get(f"http://127.0.0.1:{port}/health", timeout=1.0)
                    if resp.status_code == 200:
                        ready = True
                        break
                except httpx.RequestError:
                    pass
                time.sleep(0.3)
            estado = "OK" if ready else "SIN RESPUESTA"
            print(f"  [*] {name:<22} -> {estado} (Swagger: http://127.0.0.1:{port}/docs)")

        print("\n" + "=" * 68)
        print(f"  Cliente Web y API Gateway : http://127.0.0.1:{settings.gateway_port}")
        print(f"  Catálogo SOA en vivo      : http://127.0.0.1:{settings.gateway_port}/registry/services")
        print("  Presiona Ctrl+C para detener todos los servicios.")
        print("=" * 68 + "\n")

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo servicios SOA...")
    finally:
        for name, proc, _ in processes:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            print(f"  [-] {name} detenido.")


if __name__ == "__main__":
    main()

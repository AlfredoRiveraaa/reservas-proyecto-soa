"""Carga datos semilla realistas a través del API Gateway de ReservaSOA."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from shared.config import get_settings


def main() -> None:
    settings = get_settings()
    base = f"http://127.0.0.1:{settings.gateway_port}"

    users = [
        {
            "full_name": "Administrador NexoSalas",
            "email": "admin@nexosalas.com",
            "department": "Operaciones TI",
            "password": "Admin123!",
            "role": "admin",
        },
        {
            "full_name": "Ana López Morales",
            "email": "ana.lopez@nexosalas.com",
            "department": "Ingeniería de Software",
            "password": "Ana12345",
            "role": "employee",
        },
        {
            "full_name": "Carlos Méndez Ruiz",
            "email": "carlos.mendez@nexosalas.com",
            "department": "Diseño de Producto",
            "password": "Carlos123",
            "role": "employee",
        },
    ]

    spaces = [
        {
            "code": "SALA-A1",
            "name": "Sala Innovación Norte",
            "building": "Edificio Central",
            "floor": 2,
            "capacity": 12,
            "resources": ["Proyector 4K", "Pizarra inteligente", "Videoconferencia"],
            "status": "available",
            "description": "Sala equipada para sesiones de arquitectura y demostraciones.",
        },
        {
            "code": "SALA-B2",
            "name": "Sala Colaborativa Ágil",
            "building": "Edificio Central",
            "floor": 3,
            "capacity": 8,
            "resources": ["Pantalla 65\"", "Pizarrón acrílico", "Audio ambiental"],
            "status": "available",
            "description": "Ideal para dailies, retrospectivas y mesas de trabajo.",
        },
        {
            "code": "AUD-01",
            "name": "Auditorio NexoSalas",
            "building": "Torre Innovación",
            "floor": 1,
            "capacity": 80,
            "resources": ["Doble proyector", "Sonido envolvente", "Streaming HD", "Podio"],
            "status": "available",
            "description": "Auditorio principal para presentaciones ejecutivas.",
        },
        {
            "code": "LAB-C1",
            "name": "Laboratorio de Prototipos",
            "building": "Torre Innovación",
            "floor": 4,
            "capacity": 16,
            "resources": ["Mesas modulares", "Red 10Gbps", "Monitor interactivo"],
            "status": "available",
            "description": "Espacio técnico para talleres prácticos.",
        },
        {
            "code": "SALA-M9",
            "name": "Sala Ejecutiva Poniente",
            "building": "Edificio Anexo",
            "floor": 2,
            "capacity": 6,
            "resources": ["Videoconferencia", "Café bar"],
            "status": "maintenance",
            "description": "En mantenimiento preventivo de climatización.",
        },
    ]

    with httpx.Client(timeout=10.0) as client:
        print("1) Registrando usuarios iniciales...")
        for user in users:
            resp = client.post(f"{base}/api/auth/register", json=user)
            if resp.status_code == 201:
                print(f"   [+] Usuario creado: {user['email']} ({user['role']})")
            elif resp.status_code == 409:
                print(f"   [=] Usuario ya existente: {user['email']}")
            else:
                print(f"   [!] Error creando {user['email']}: {resp.status_code} {resp.text}")

        login_resp = client.post(
            f"{base}/api/auth/login",
            json={"email": "admin@nexosalas.com", "password": "Admin123!"},
        )
        login_resp.raise_for_status()
        admin_token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        print("2) Registrando salas y recursos iniciales...")
        created_spaces: list[dict] = []
        for space in spaces:
            resp = client.post(f"{base}/api/spaces", json=space, headers=headers)
            if resp.status_code == 201:
                print(f"   [+] Espacio creado: {space['code']} - {space['name']}")
                created_spaces.append(resp.json())
            elif resp.status_code == 409:
                print(f"   [=] Espacio ya existente: {space['code']}")

        all_spaces = client.get(f"{base}/api/spaces").json()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        print("3) Creando reservación de demostración orquestada (E2E)...")
        if all_spaces:
            sample_res = {
                "space_id": all_spaces[0]["id"],
                "title": "Revisión de Arquitectura SOA",
                "reservation_date": tomorrow,
                "start_time": "10:00",
                "end_time": "11:30",
                "attendees": 8,
                "notes": "Demostración en vivo de integración de servicios.",
            }
            resp = client.post(f"{base}/api/reservations", json=sample_res, headers=headers)
            if resp.status_code == 201:
                body = resp.json()
                print(
                    f"   [+] Reservación #{body['id']} confirmada "
                    f"(Folio: {body['confirmation_code']})"
                )
            elif resp.status_code == 409:
                print("   [=] La reservación de demostración ya existe para ese horario.")
            else:
                print(f"   [!] Error creando reservación demo: {resp.status_code} {resp.text}")

    print("\nDatos semilla cargados correctamente.")


if __name__ == "__main__":
    main()

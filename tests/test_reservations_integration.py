"""Pruebas de integración E2E SOA y manejo de errores en reservations-service."""

from __future__ import annotations


def _create_sample_space(soa_env, code: str = "SALA-A1", capacity: int = 12, status: str = "available"):
    resp = soa_env["spaces_client"].post(
        "/spaces",
        headers=soa_env["admin_headers"],
        json={
            "code": code,
            "name": f"Sala {code}",
            "building": "Edificio Central",
            "floor": 2,
            "capacity": capacity,
            "resources": ["Proyector 4K", "Videoconferencia"],
            "status": status,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_end_to_end_reservation_lifecycle(soa_env):
    """Flujo E2E completo: crear sala -> reservar (4 servicios) -> modificar -> cancelar."""
    space = _create_sample_space(soa_env)
    res_client = soa_env["reservations_client"]
    notif_client = soa_env["notifications_client"]
    emp_headers = soa_env["emp_headers"]

    # 1) Crear reservación orquestada
    created = res_client.post(
        "/reservations",
        headers=emp_headers,
        json={
            "space_id": space["id"],
            "title": "Revisión Arquitectura SOA",
            "reservation_date": "2026-12-10",
            "start_time": "10:00",
            "end_time": "11:30",
            "attendees": 8,
            "notes": "Demo en vivo",
        },
    )
    assert created.status_code == 201
    reservation = created.json()
    assert reservation["status"] == "CONFIRMED"
    assert reservation["confirmation_code"].startswith("CONF-")
    assert len(reservation["soa_trace"]) == 4
    services_touched = [step["service"] for step in reservation["soa_trace"]]
    assert services_touched == [
        "users-service",
        "spaces-service",
        "reservations-service",
        "notifications-service",
    ]

    # Verificar que notifications-service persistió la confirmación en su propia BD
    notifs = notif_client.get(
        "/notifications",
        params={"reservation_id": reservation["id"]},
        headers=emp_headers,
    ).json()
    assert len(notifs) == 1
    assert notifs[0]["confirmation_code"] == reservation["confirmation_code"]

    # 2) Intentar traslape de horario en la misma sala -> 409 Conflict
    overlap = res_client.post(
        "/reservations",
        headers=emp_headers,
        json={
            "space_id": space["id"],
            "title": "Reunión Traslapada",
            "reservation_date": "2026-12-10",
            "start_time": "11:00",
            "end_time": "12:00",
            "attendees": 4,
        },
    )
    assert overlap.status_code == 409
    assert overlap.json()["error_code"] == "RESOURCE_CONFLICT"

    # 3) Modificar reservación
    updated = res_client.put(
        f"/reservations/{reservation['id']}",
        headers=emp_headers,
        json={"title": "Revisión Arquitectura SOA (Actualizada)", "attendees": 10},
    )
    assert updated.status_code == 200
    assert updated.json()["attendees"] == 10

    # 4) Cancelar reservación -> emite notificación de cancelación y libera horario
    cancelled = res_client.post(
        f"/reservations/{reservation['id']}/cancel",
        headers=emp_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    # Verificar que el horario quedó libre para una nueva reserva
    rebooked = res_client.post(
        "/reservations",
        headers=emp_headers,
        json={
            "space_id": space["id"],
            "title": "Nueva Reserva en Horario Liberado",
            "reservation_date": "2026-12-10",
            "start_time": "10:00",
            "end_time": "11:00",
            "attendees": 5,
        },
    )
    assert rebooked.status_code == 201


def test_reservation_business_rules_and_upstream_failures(soa_env):
    """Valida reglas de capacidad, mantenimiento, horarios inválidos y caídas de servicios."""
    small_space = _create_sample_space(soa_env, code="SALA-S1", capacity=4)
    maint_space = _create_sample_space(soa_env, code="SALA-M1", capacity=10, status="maintenance")
    res_client = soa_env["reservations_client"]
    emp_headers = soa_env["emp_headers"]

    # Exceso de capacidad -> 422
    too_many = res_client.post(
        "/reservations",
        headers=emp_headers,
        json={
            "space_id": small_space["id"],
            "title": "Reunión Masiva",
            "reservation_date": "2026-12-12",
            "start_time": "09:00",
            "end_time": "10:00",
            "attendees": 15,
        },
    )
    assert too_many.status_code == 422

    # Sala en mantenimiento -> 422
    in_maint = res_client.post(
        "/reservations",
        headers=emp_headers,
        json={
            "space_id": maint_space["id"],
            "title": "Reunión en Sala Cerrada",
            "reservation_date": "2026-12-12",
            "start_time": "09:00",
            "end_time": "10:00",
            "attendees": 2,
        },
    )
    assert in_maint.status_code == 422

    # Hora fin menor que inicio -> 422
    bad_hours = res_client.post(
        "/reservations",
        headers=emp_headers,
        json={
            "space_id": small_space["id"],
            "title": "Horario Invertido",
            "reservation_date": "2026-12-12",
            "start_time": "14:00",
            "end_time": "13:00",
            "attendees": 2,
        },
    )
    assert bad_hours.status_code == 422

    # Falla de comunicación con spaces-service -> 503
    soa_env["spaces_http"].simulate_down = True
    down_spaces = res_client.post(
        "/reservations",
        headers=emp_headers,
        json={
            "space_id": small_space["id"],
            "title": "Prueba Caída Spaces",
            "reservation_date": "2026-12-12",
            "start_time": "15:00",
            "end_time": "16:00",
            "attendees": 2,
        },
    )
    assert down_spaces.status_code == 503
    assert down_spaces.json()["error_code"] == "UPSTREAM_UNAVAILABLE"
    soa_env["spaces_http"].simulate_down = False

    # Degradación controlada si notifications-service está caído
    soa_env["notifications_http"].simulate_down = True
    degraded = res_client.post(
        "/reservations",
        headers=emp_headers,
        json={
            "space_id": small_space["id"],
            "title": "Prueba Resiliencia Notificaciones",
            "reservation_date": "2026-12-12",
            "start_time": "16:00",
            "end_time": "17:00",
            "attendees": 3,
        },
    )
    assert degraded.status_code == 201
    assert degraded.json()["confirmation_code"] == "PENDING-RETRY"
    assert degraded.json()["soa_trace"][-1]["status"] == "DEGRADED"

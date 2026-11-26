"""Pruebas CRUD y emisión de folios de notifications-service."""

from __future__ import annotations


def test_notifications_crud_flow(soa_env):
    client = soa_env["notifications_client"]
    admin_headers = soa_env["admin_headers"]
    emp_headers = soa_env["emp_headers"]

    created = client.post(
        "/notifications",
        headers=emp_headers,
        json={
            "reservation_id": 10,
            "user_id": soa_env["emp_user"]["id"],
            "recipient_email": "ana@espaciohub.com",
            "recipient_name": "Ana López",
            "event_type": "RESERVATION_CONFIRMED",
            "subject": "Confirmación Sala A1",
            "message": "Tu reserva fue confirmada exitosamente.",
            "channel": "EMAIL",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["confirmation_code"].startswith("CONF-")
    notif_id = body["id"]

    # Consultar listado filtrado
    listed = client.get("/notifications", params={"reservation_id": 10}, headers=emp_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    # Actualizar estado a READ
    patched = client.patch(
        f"/notifications/{notif_id}/status",
        headers=emp_headers,
        json={"status": "READ"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "READ"

    # Eliminar notificación (admin)
    assert client.delete(f"/notifications/{notif_id}", headers=admin_headers).status_code == 204
    assert client.get(f"/notifications/{notif_id}", headers=admin_headers).status_code == 404

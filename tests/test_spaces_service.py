"""Pruebas CRUD, filtros y validación SOA de spaces-service."""

from __future__ import annotations


def test_spaces_crud_and_validation_endpoint(soa_env):
    client = soa_env["spaces_client"]
    admin_headers = soa_env["admin_headers"]
    emp_headers = soa_env["emp_headers"]

    # Crear sala
    created = client.post(
        "/spaces",
        headers=admin_headers,
        json={
            "code": "SALA-A1",
            "name": "Sala Innovación Norte",
            "building": "Edificio Central",
            "floor": 2,
            "capacity": 10,
            "resources": ["Proyector 4K", "Pizarra"],
            "status": "available",
        },
    )
    assert created.status_code == 201
    space_id = created.json()["id"]

    # Duplicar código -> 409
    dup = client.post(
        "/spaces",
        headers=admin_headers,
        json={
            "code": "SALA-A1",
            "name": "Otra Sala",
            "building": "Central",
            "floor": 1,
            "capacity": 5,
        },
    )
    assert dup.status_code == 409

    # Filtros por capacidad y recurso
    filtered = client.get("/spaces", params={"min_capacity": 8, "resource": "proyector"})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    # Validación SOA exitosa y fallida por exceso de capacidad
    ok_val = client.get(f"/spaces/{space_id}/validate", params={"attendees": 8}, headers=emp_headers)
    assert ok_val.status_code == 200
    assert ok_val.json()["valid"] is True

    bad_cap = client.get(
        f"/spaces/{space_id}/validate", params={"attendees": 25}, headers=emp_headers
    )
    assert bad_cap.status_code == 200
    assert bad_cap.json()["valid"] is False

    # Actualizar a mantenimiento y verificar validación
    upd = client.put(
        f"/spaces/{space_id}",
        headers=admin_headers,
        json={"status": "maintenance"},
    )
    assert upd.status_code == 200
    assert upd.json()["status"] == "maintenance"

    maint_val = client.get(
        f"/spaces/{space_id}/validate", params={"attendees": 4}, headers=emp_headers
    )
    assert maint_val.json()["valid"] is False

    # Eliminar espacio
    assert client.delete(f"/spaces/{space_id}", headers=admin_headers).status_code == 204
    assert client.get(f"/spaces/{space_id}").status_code == 404

"""Pruebas CRUD, autenticación JWT y validaciones de users-service."""

from __future__ import annotations


def test_users_crud_and_auth_flow(soa_env):
    client = soa_env["users_client"]
    admin_headers = soa_env["admin_headers"]
    emp_headers = soa_env["emp_headers"]

    # Salud
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["service"] == "users-service"

    # Perfil actual con JWT
    me = client.get("/auth/me", headers=emp_headers)
    assert me.status_code == 200
    assert me.json()["email"] == "ana@espaciohub.com"

    # Crear usuario por admin
    created = client.post(
        "/users",
        headers=admin_headers,
        json={
            "full_name": "Carlos Méndez",
            "email": "carlos@espaciohub.com",
            "department": "Producto",
            "password": "Carlos123",
            "role": "employee",
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]

    # Consultar lista y detalle
    listed = client.get("/users", headers=emp_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 3

    detail = client.get(f"/users/{user_id}", headers=emp_headers)
    assert detail.status_code == 200
    assert detail.json()["department"] == "Producto"

    # Actualizar usuario
    updated = client.put(
        f"/users/{user_id}",
        headers=admin_headers,
        json={"department": "Arquitectura", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["department"] == "Arquitectura"
    assert updated.json()["is_active"] is False

    # Usuario inactivo no puede iniciar sesión
    login_inactive = client.post(
        "/auth/login",
        json={"email": "carlos@espaciohub.com", "password": "Carlos123"},
    )
    assert login_inactive.status_code == 403

    # Eliminar usuario
    deleted = client.delete(f"/users/{user_id}", headers=admin_headers)
    assert deleted.status_code == 204
    assert client.get(f"/users/{user_id}", headers=admin_headers).status_code == 404


def test_users_security_and_validation_errors(soa_env):
    client = soa_env["users_client"]
    emp_headers = soa_env["emp_headers"]

    # Sin token -> 401
    assert client.get("/users").status_code == 401

    # Empleado intentando crear usuario -> 403
    forbidden = client.post(
        "/users",
        headers=emp_headers,
        json={
            "full_name": "Sin Permiso",
            "email": "no@espaciohub.com",
            "department": "Ventas",
            "password": "Password123",
        },
    )
    assert forbidden.status_code == 403

    # Correo duplicado -> 409
    dup = client.post(
        "/auth/register",
        json={
            "full_name": "Duplicado",
            "email": "ana@espaciohub.com",
            "department": "Ingeniería",
            "password": "Password123",
        },
    )
    assert dup.status_code == 409

    # Datos inválidos -> 422
    invalid = client.post(
        "/auth/register",
        json={
            "full_name": "A",
            "email": "no-es-correo",
            "department": "X",
            "password": "123",
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["error_code"] == "INPUT_VALIDATION_ERROR"

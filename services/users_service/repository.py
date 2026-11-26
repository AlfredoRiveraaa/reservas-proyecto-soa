"""Repositorio CRUD para la entidad Usuario en users-service."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from services.users_service.database import UsersDatabase
from services.users_service.models import UserCreate, UserResponse, UserUpdate
from shared.errors import ConflictError, NotFoundError
from shared.security import hash_password


class UserRepository:
    """Encapsula las operaciones de persistencia de usuarios."""

    def __init__(self, db: UsersDatabase) -> None:
        self.db = db

    @staticmethod
    def _row_to_response(row: sqlite3.Row) -> UserResponse:
        return UserResponse(
            id=row["id"],
            full_name=row["full_name"],
            email=row["email"],
            department=row["department"],
            role=row["role"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(self, payload: UserCreate) -> UserResponse:
        now = datetime.now(timezone.utc).isoformat()
        password_hash = hash_password(payload.password)
        try:
            with self.db.connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO users (
                        full_name, email, department, role, password_hash,
                        is_active, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        payload.full_name.strip(),
                        payload.email.lower().strip(),
                        payload.department.strip(),
                        payload.role,
                        password_hash,
                        now,
                        now,
                    ),
                )
                conn.commit()
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise ConflictError(
                f"Ya existe un usuario registrado con el correo '{payload.email}'."
            ) from exc

        return self.get_by_id(int(user_id))

    def list_all(self, only_active: bool = False) -> list[UserResponse]:
        query = "SELECT * FROM users"
        if only_active:
            query += " WHERE is_active = 1"
        query += " ORDER BY id ASC"
        with self.db.connect() as conn:
            rows = conn.execute(query).fetchall()
        return [self._row_to_response(row) for row in rows]

    def get_by_id(self, user_id: int) -> UserResponse:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"No se encontró el usuario con id {user_id}.")
        return self._row_to_response(row)

    def get_auth_record_by_email(self, email: str) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def update(self, user_id: int, payload: UserUpdate) -> UserResponse:
        existing = self.get_by_id(user_id)
        updated_full_name = (
            payload.full_name.strip() if payload.full_name is not None else existing.full_name
        )
        updated_department = (
            payload.department.strip() if payload.department is not None else existing.department
        )
        updated_role = payload.role if payload.role is not None else existing.role
        updated_active = (
            int(payload.is_active) if payload.is_active is not None else int(existing.is_active)
        )
        now = datetime.now(timezone.utc).isoformat()

        with self.db.connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, department = ?, role = ?, is_active = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    updated_full_name,
                    updated_department,
                    updated_role,
                    updated_active,
                    now,
                    user_id,
                ),
            )
            conn.commit()
        return self.get_by_id(user_id)

    def delete(self, user_id: int) -> None:
        self.get_by_id(user_id)
        with self.db.connect() as conn:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

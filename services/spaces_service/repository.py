"""Repositorio CRUD para salas y recursos en spaces-service."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from services.spaces_service.database import SpacesDatabase
from services.spaces_service.models import SpaceCreate, SpaceResponse, SpaceUpdate
from shared.errors import ConflictError, NotFoundError


class SpaceRepository:
    """Encapsula las operaciones de persistencia de espacios físicos."""

    def __init__(self, db: SpacesDatabase) -> None:
        self.db = db

    @staticmethod
    def _row_to_response(row: sqlite3.Row) -> SpaceResponse:
        return SpaceResponse(
            id=row["id"],
            code=row["code"],
            name=row["name"],
            building=row["building"],
            floor=row["floor"],
            capacity=row["capacity"],
            resources=json.loads(row["resources_json"]),
            status=row["status"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(self, payload: SpaceCreate) -> SpaceResponse:
        now = datetime.now(timezone.utc).isoformat()
        clean_resources = [item.strip() for item in payload.resources if item.strip()]
        try:
            with self.db.connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO spaces (
                        code, name, building, floor, capacity, resources_json,
                        status, description, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.code.upper().strip(),
                        payload.name.strip(),
                        payload.building.strip(),
                        payload.floor,
                        payload.capacity,
                        json.dumps(clean_resources, ensure_ascii=False),
                        payload.status,
                        payload.description.strip(),
                        now,
                        now,
                    ),
                )
                conn.commit()
                space_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            raise ConflictError(
                f"Ya existe un espacio registrado con el código '{payload.code.upper()}'."
            ) from exc

        return self.get_by_id(int(space_id))

    def list_all(
        self,
        status_filter: str | None = None,
        min_capacity: int | None = None,
        building: str | None = None,
        resource: str | None = None,
    ) -> list[SpaceResponse]:
        clauses: list[str] = []
        params: list[object] = []

        if status_filter:
            clauses.append("status = ?")
            params.append(status_filter)
        if min_capacity is not None:
            clauses.append("capacity >= ?")
            params.append(min_capacity)
        if building:
            clauses.append("LOWER(building) LIKE ?")
            params.append(f"%{building.lower().strip()}%")

        query = "SELECT * FROM spaces"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id ASC"

        with self.db.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        results = [self._row_to_response(row) for row in rows]
        if resource:
            needle = resource.lower().strip()
            results = [
                space
                for space in results
                if any(needle in item.lower() for item in space.resources)
            ]
        return results

    def get_by_id(self, space_id: int) -> SpaceResponse:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM spaces WHERE id = ?", (space_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"No se encontró el espacio con id {space_id}.")
        return self._row_to_response(row)

    def update(self, space_id: int, payload: SpaceUpdate) -> SpaceResponse:
        existing = self.get_by_id(space_id)
        updated_resources = (
            [item.strip() for item in payload.resources if item.strip()]
            if payload.resources is not None
            else existing.resources
        )
        now = datetime.now(timezone.utc).isoformat()

        with self.db.connect() as conn:
            conn.execute(
                """
                UPDATE spaces
                SET name = ?, building = ?, floor = ?, capacity = ?,
                    resources_json = ?, status = ?, description = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.name.strip() if payload.name is not None else existing.name,
                    payload.building.strip() if payload.building is not None else existing.building,
                    payload.floor if payload.floor is not None else existing.floor,
                    payload.capacity if payload.capacity is not None else existing.capacity,
                    json.dumps(updated_resources, ensure_ascii=False),
                    payload.status if payload.status is not None else existing.status,
                    payload.description.strip()
                    if payload.description is not None
                    else existing.description,
                    now,
                    space_id,
                ),
            )
            conn.commit()
        return self.get_by_id(space_id)

    def delete(self, space_id: int) -> None:
        self.get_by_id(space_id)
        with self.db.connect() as conn:
            conn.execute("DELETE FROM spaces WHERE id = ?", (space_id,))
            conn.commit()

"""Repositorio CRUD y detección de traslapes de horario para reservations-service."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from services.reservations_service.database import ReservationsDatabase
from services.reservations_service.models import ReservationResponse, ReservationStatus
from shared.errors import NotFoundError


class ReservationRepository:
    """Encapsula las operaciones de persistencia de reservaciones."""

    def __init__(self, db: ReservationsDatabase) -> None:
        self.db = db

    @staticmethod
    def _row_to_response(row: sqlite3.Row) -> ReservationResponse:
        return ReservationResponse(
            id=row["id"],
            user_id=row["user_id"],
            user_name=row["user_name"],
            user_email=row["user_email"],
            space_id=row["space_id"],
            space_code=row["space_code"],
            space_name=row["space_name"],
            title=row["title"],
            reservation_date=row["reservation_date"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            attendees=row["attendees"],
            notes=row["notes"],
            status=row["status"],
            confirmation_code=row["confirmation_code"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def has_time_conflict(
        self,
        space_id: int,
        reservation_date: str,
        start_time: str,
        end_time: str,
        exclude_reservation_id: int | None = None,
    ) -> bool:
        """Comprueba si existe otra reservación CONFIRMED que se traslape en la misma sala."""
        query = """
            SELECT COUNT(1) AS total
            FROM reservations
            WHERE space_id = ?
              AND reservation_date = ?
              AND status = 'CONFIRMED'
              AND start_time < ?
              AND end_time > ?
        """
        params: list[object] = [space_id, reservation_date, end_time, start_time]
        if exclude_reservation_id is not None:
            query += " AND id != ?"
            params.append(exclude_reservation_id)

        with self.db.connect() as conn:
            row = conn.execute(query, params).fetchone()
        return int(row["total"]) > 0

    def create(
        self,
        *,
        user_id: int,
        user_name: str,
        user_email: str,
        space_id: int,
        space_code: str,
        space_name: str,
        title: str,
        reservation_date: str,
        start_time: str,
        end_time: str,
        attendees: int,
        notes: str,
        confirmation_code: str = "",
    ) -> ReservationResponse:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reservations (
                    user_id, user_name, user_email, space_id, space_code, space_name,
                    title, reservation_date, start_time, end_time, attendees, notes,
                    status, confirmation_code, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?, ?, ?)
                """,
                (
                    user_id,
                    user_name,
                    user_email,
                    space_id,
                    space_code,
                    space_name,
                    title.strip(),
                    reservation_date,
                    start_time,
                    end_time,
                    attendees,
                    notes.strip(),
                    confirmation_code,
                    now,
                    now,
                ),
            )
            conn.commit()
            reservation_id = cursor.lastrowid
        return self.get_by_id(int(reservation_id))

    def list_all(
        self,
        user_id: int | None = None,
        space_id: int | None = None,
        reservation_date: str | None = None,
        status_filter: ReservationStatus | None = None,
    ) -> list[ReservationResponse]:
        clauses: list[str] = []
        params: list[object] = []

        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if space_id is not None:
            clauses.append("space_id = ?")
            params.append(space_id)
        if reservation_date:
            clauses.append("reservation_date = ?")
            params.append(reservation_date)
        if status_filter:
            clauses.append("status = ?")
            params.append(status_filter)

        query = "SELECT * FROM reservations"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY reservation_date DESC, start_time ASC"

        with self.db.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_response(row) for row in rows]

    def get_by_id(self, reservation_id: int) -> ReservationResponse:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"No se encontró la reservación con id {reservation_id}.")
        return self._row_to_response(row)

    def set_confirmation_code(self, reservation_id: int, code: str) -> ReservationResponse:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE reservations SET confirmation_code = ?, updated_at = ? WHERE id = ?",
                (code, now, reservation_id),
            )
            conn.commit()
        return self.get_by_id(reservation_id)

    def update(
        self,
        reservation_id: int,
        *,
        title: str,
        reservation_date: str,
        start_time: str,
        end_time: str,
        attendees: int,
        notes: str,
    ) -> ReservationResponse:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connect() as conn:
            conn.execute(
                """
                UPDATE reservations
                SET title = ?, reservation_date = ?, start_time = ?, end_time = ?,
                    attendees = ?, notes = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    title.strip(),
                    reservation_date,
                    start_time,
                    end_time,
                    attendees,
                    notes.strip(),
                    now,
                    reservation_id,
                ),
            )
            conn.commit()
        return self.get_by_id(reservation_id)

    def cancel(self, reservation_id: int) -> ReservationResponse:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE reservations SET status = 'CANCELLED', updated_at = ? WHERE id = ?",
                (now, reservation_id),
            )
            conn.commit()
        return self.get_by_id(reservation_id)

    def delete(self, reservation_id: int) -> None:
        self.get_by_id(reservation_id)
        with self.db.connect() as conn:
            conn.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
            conn.commit()

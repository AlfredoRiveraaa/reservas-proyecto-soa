"""Repositorio CRUD de notificaciones y emisión de folios de confirmación."""

from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timezone

from services.notifications_service.database import NotificationsDatabase
from services.notifications_service.models import (
    NotificationCreate,
    NotificationResponse,
    NotificationStatus,
)
from shared.errors import NotFoundError


class NotificationRepository:
    """Encapsula la persistencia y generación de comprobantes de reservación."""

    def __init__(self, db: NotificationsDatabase) -> None:
        self.db = db

    @staticmethod
    def _generate_confirmation_code() -> str:
        year = datetime.now(timezone.utc).year
        token = secrets.token_hex(3).upper()
        return f"CONF-{year}-{token}"

    @staticmethod
    def _row_to_response(row: sqlite3.Row) -> NotificationResponse:
        return NotificationResponse(
            id=row["id"],
            confirmation_code=row["confirmation_code"],
            reservation_id=row["reservation_id"],
            user_id=row["user_id"],
            recipient_email=row["recipient_email"],
            recipient_name=row["recipient_name"],
            event_type=row["event_type"],
            subject=row["subject"],
            message=row["message"],
            channel=row["channel"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(self, payload: NotificationCreate) -> NotificationResponse:
        now = datetime.now(timezone.utc).isoformat()
        code = self._generate_confirmation_code()
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO notifications (
                    confirmation_code, reservation_id, user_id, recipient_email,
                    recipient_name, event_type, subject, message, channel, status,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'SENT', ?, ?)
                """,
                (
                    code,
                    payload.reservation_id,
                    payload.user_id,
                    payload.recipient_email.lower().strip(),
                    payload.recipient_name.strip(),
                    payload.event_type,
                    payload.subject.strip(),
                    payload.message.strip(),
                    payload.channel,
                    now,
                    now,
                ),
            )
            conn.commit()
            notification_id = cursor.lastrowid
        return self.get_by_id(int(notification_id))

    def list_all(
        self,
        user_id: int | None = None,
        reservation_id: int | None = None,
        event_type: str | None = None,
    ) -> list[NotificationResponse]:
        clauses: list[str] = []
        params: list[object] = []
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if reservation_id is not None:
            clauses.append("reservation_id = ?")
            params.append(reservation_id)
        if event_type:
            clauses.append("event_type = ?")
            params.append(event_type)

        query = "SELECT * FROM notifications"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC"

        with self.db.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_response(row) for row in rows]

    def get_by_id(self, notification_id: int) -> NotificationResponse:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM notifications WHERE id = ?", (notification_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"No se encontró la notificación con id {notification_id}.")
        return self._row_to_response(row)

    def update_status(self, notification_id: int, new_status: NotificationStatus) -> NotificationResponse:
        self.get_by_id(notification_id)
        now = datetime.now(timezone.utc).isoformat()
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE notifications SET status = ?, updated_at = ? WHERE id = ?",
                (new_status, now, notification_id),
            )
            conn.commit()
        return self.get_by_id(notification_id)

    def delete(self, notification_id: int) -> None:
        self.get_by_id(notification_id)
        with self.db.connect() as conn:
            conn.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
            conn.commit()

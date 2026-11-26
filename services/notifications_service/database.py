"""Gestión de la base de datos SQLite independiente para notifications-service."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from shared.config import get_settings


class NotificationsDatabase:
    """Administra la conexión y esquema propio del Servicio de Notificaciones."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_settings().db_path("notifications.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    confirmation_code TEXT NOT NULL UNIQUE,
                    reservation_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    recipient_email TEXT NOT NULL,
                    recipient_name TEXT NOT NULL,
                    event_type TEXT NOT NULL CHECK(
                        event_type IN (
                            'RESERVATION_CONFIRMED',
                            'RESERVATION_UPDATED',
                            'RESERVATION_CANCELLED'
                        )
                    ),
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    channel TEXT NOT NULL CHECK(channel IN ('EMAIL', 'IN_APP')),
                    status TEXT NOT NULL CHECK(status IN ('SENT', 'READ', 'FAILED')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

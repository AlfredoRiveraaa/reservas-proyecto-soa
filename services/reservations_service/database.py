"""Gestión de la base de datos SQLite independiente para reservations-service."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from shared.config import get_settings


class ReservationsDatabase:
    """Administra la conexión y esquema propio del Servicio de Reservaciones."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_settings().db_path("reservations.db")
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
                CREATE TABLE IF NOT EXISTS reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    space_id INTEGER NOT NULL,
                    space_code TEXT NOT NULL,
                    space_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    reservation_date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    attendees INTEGER NOT NULL CHECK(attendees > 0),
                    notes TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL CHECK(status IN ('CONFIRMED', 'CANCELLED')),
                    confirmation_code TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reservations_slot
                ON reservations (space_id, reservation_date, status)
                """
            )
            conn.commit()

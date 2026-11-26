"""Gestión de la base de datos SQLite independiente para spaces-service."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from shared.config import get_settings


class SpacesDatabase:
    """Administra la conexión y esquema propio del Servicio de Espacios."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_settings().db_path("spaces.db")
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
                CREATE TABLE IF NOT EXISTS spaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    building TEXT NOT NULL,
                    floor INTEGER NOT NULL,
                    capacity INTEGER NOT NULL CHECK(capacity > 0),
                    resources_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL CHECK(status IN ('available', 'maintenance')),
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

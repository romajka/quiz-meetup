from __future__ import annotations

from quiz_meetup.database.connection import Database


class SettingsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_all(self) -> dict[str, str]:
        rows = self.database.fetchall("SELECT key, value FROM settings ORDER BY key ASC")
        return {row["key"]: row["value"] for row in rows}

    def get(self, key: str) -> str | None:
        row = self.database.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        if row is None:
            return None
        return row["value"]

    def set(self, key: str, value: str) -> None:
        self.database.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

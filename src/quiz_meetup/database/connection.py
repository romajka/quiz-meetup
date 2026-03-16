from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON;")

    def execute(self, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(sql, parameters)
        self.connection.commit()
        return cursor

    def fetchall(self, sql: str, parameters: tuple = ()) -> list[sqlite3.Row]:
        cursor = self.connection.execute(sql, parameters)
        return cursor.fetchall()

    def fetchone(self, sql: str, parameters: tuple = ()) -> sqlite3.Row | None:
        cursor = self.connection.execute(sql, parameters)
        return cursor.fetchone()

    def executescript(self, script: str) -> None:
        self.connection.executescript(script)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

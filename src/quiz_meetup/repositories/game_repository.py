from __future__ import annotations

from datetime import datetime

from quiz_meetup.database.connection import Database
from quiz_meetup.models import Game


class GameRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, title: str, description: str) -> Game:
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        cursor = self.database.execute(
            """
            INSERT INTO games (title, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (title, description, timestamp, timestamp),
        )
        return self.get_by_id(cursor.lastrowid)

    def update(self, game_id: int, title: str, description: str) -> Game | None:
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        self.database.execute(
            """
            UPDATE games
            SET title = ?, description = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, description, timestamp, game_id),
        )
        return self.get_by_id(game_id)

    def delete(self, game_id: int) -> None:
        self.database.execute("DELETE FROM games WHERE id = ?", (game_id,))

    def list_all(self) -> list[Game]:
        rows = self.database.fetchall(
            "SELECT * FROM games ORDER BY updated_at DESC, id DESC"
        )
        return [self._row_to_game(row) for row in rows]

    def get_by_id(self, game_id: int) -> Game | None:
        row = self.database.fetchone("SELECT * FROM games WHERE id = ?", (game_id,))
        if row is None:
            return None
        return self._row_to_game(row)

    @staticmethod
    def _row_to_game(row) -> Game:
        return Game(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

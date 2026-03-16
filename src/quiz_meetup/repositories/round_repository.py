from __future__ import annotations

from quiz_meetup.database.connection import Database
from quiz_meetup.models import Round


class RoundRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(
        self,
        game_id: int,
        title: str,
        order_index: int,
        timer_seconds: int,
        notes: str,
    ) -> Round:
        cursor = self.database.execute(
            """
            INSERT INTO rounds (game_id, title, order_index, timer_seconds, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (game_id, title, order_index, timer_seconds, notes),
        )
        return self.get_by_id(cursor.lastrowid)

    def update(
        self,
        round_id: int,
        title: str,
        timer_seconds: int,
        notes: str,
    ) -> Round | None:
        self.database.execute(
            """
            UPDATE rounds
            SET title = ?, timer_seconds = ?, notes = ?
            WHERE id = ?
            """,
            (title, timer_seconds, notes, round_id),
        )
        return self.get_by_id(round_id)

    def update_order(self, round_id: int, order_index: int) -> None:
        self.database.execute(
            "UPDATE rounds SET order_index = ? WHERE id = ?",
            (order_index, round_id),
        )

    def delete(self, round_id: int) -> None:
        self.database.execute("DELETE FROM rounds WHERE id = ?", (round_id,))

    def get_next_order_index(self, game_id: int) -> int:
        row = self.database.fetchone(
            "SELECT COALESCE(MAX(order_index), 0) + 1 AS next_index FROM rounds WHERE game_id = ?",
            (game_id,),
        )
        return row["next_index"] if row is not None else 1

    def list_by_game(self, game_id: int) -> list[Round]:
        rows = self.database.fetchall(
            """
            SELECT * FROM rounds
            WHERE game_id = ?
            ORDER BY order_index ASC, id ASC
            """,
            (game_id,),
        )
        return [self._row_to_round(row) for row in rows]

    def list_all(self) -> list[Round]:
        rows = self.database.fetchall(
            "SELECT * FROM rounds ORDER BY game_id ASC, order_index ASC, id ASC"
        )
        return [self._row_to_round(row) for row in rows]

    def get_by_id(self, round_id: int) -> Round | None:
        row = self.database.fetchone("SELECT * FROM rounds WHERE id = ?", (round_id,))
        if row is None:
            return None
        return self._row_to_round(row)

    @staticmethod
    def _row_to_round(row) -> Round:
        return Round(
            id=row["id"],
            game_id=row["game_id"],
            title=row["title"],
            order_index=row["order_index"],
            timer_seconds=row["timer_seconds"],
            notes=row["notes"],
        )

from __future__ import annotations

from datetime import datetime

from quiz_meetup.database.connection import Database
from quiz_meetup.models import GameSession


class GameSessionRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, game_id: int) -> GameSession:
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        self.database.execute(
            """
            UPDATE game_sessions
            SET status = 'finished', updated_at = ?, finished_at = COALESCE(finished_at, ?)
            WHERE game_id = ? AND status = 'active'
            """,
            (timestamp, timestamp, game_id),
        )
        row = self.database.fetchone(
            "SELECT COALESCE(MAX(session_number), 0) + 1 AS next_number FROM game_sessions WHERE game_id = ?",
            (game_id,),
        )
        session_number = int(row["next_number"]) if row is not None else 1
        cursor = self.database.execute(
            """
            INSERT INTO game_sessions (
                game_id, session_number, status, completed_round_ids, started_at, updated_at, finished_at
            )
            VALUES (?, ?, 'active', '', ?, ?, NULL)
            """,
            (game_id, session_number, timestamp, timestamp),
        )
        return self.get_by_id(cursor.lastrowid)

    def list_by_game(self, game_id: int) -> list[GameSession]:
        rows = self.database.fetchall(
            """
            SELECT * FROM game_sessions
            WHERE game_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (game_id,),
        )
        return [self._row_to_session(row) for row in rows]

    def get_by_id(self, session_id: int) -> GameSession | None:
        row = self.database.fetchone(
            "SELECT * FROM game_sessions WHERE id = ?",
            (session_id,),
        )
        if row is None:
            return None
        return self._row_to_session(row)

    def get_active_by_game(self, game_id: int) -> GameSession | None:
        row = self.database.fetchone(
            """
            SELECT * FROM game_sessions
            WHERE game_id = ? AND status = 'active'
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (game_id,),
        )
        if row is None:
            return None
        return self._row_to_session(row)

    def touch(self, session_id: int) -> GameSession | None:
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        self.database.execute(
            "UPDATE game_sessions SET updated_at = ? WHERE id = ?",
            (timestamp, session_id),
        )
        return self.get_by_id(session_id)

    def set_completed_round_ids(self, session_id: int, completed_round_ids: list[int]) -> GameSession | None:
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        serialized_ids = ",".join(str(round_id) for round_id in sorted(set(completed_round_ids)))
        self.database.execute(
            """
            UPDATE game_sessions
            SET completed_round_ids = ?, updated_at = ?
            WHERE id = ?
            """,
            (serialized_ids, timestamp, session_id),
        )
        return self.get_by_id(session_id)

    def finish(self, session_id: int) -> GameSession | None:
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        self.database.execute(
            """
            UPDATE game_sessions
            SET status = 'finished', updated_at = ?, finished_at = COALESCE(finished_at, ?)
            WHERE id = ?
            """,
            (timestamp, timestamp, session_id),
        )
        return self.get_by_id(session_id)

    @staticmethod
    def _row_to_session(row) -> GameSession:
        return GameSession(
            id=row["id"],
            game_id=row["game_id"],
            session_number=row["session_number"],
            status=row["status"],
            completed_round_ids=row["completed_round_ids"],
            started_at=row["started_at"],
            updated_at=row["updated_at"],
            finished_at=row["finished_at"],
        )


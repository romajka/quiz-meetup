from __future__ import annotations

from datetime import datetime

from quiz_meetup.database.connection import Database
from quiz_meetup.models import Team


class TeamRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(
        self,
        game_id: int,
        name: str,
        color: str,
        session_id: int | None = None,
    ) -> Team:
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        cursor = self.database.execute(
            """
            INSERT INTO teams (game_id, session_id, name, color, score, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (game_id, session_id, name, color, timestamp),
        )
        return self.get_by_id(cursor.lastrowid)

    def list_by_game(self, game_id: int) -> list[Team]:
        rows = self.database.fetchall(
            """
            SELECT * FROM teams
            WHERE game_id = ? AND session_id IS NULL
            ORDER BY score DESC, name COLLATE NOCASE ASC, id ASC
            """,
            (game_id,),
        )
        return [self._row_to_team(row) for row in rows]

    def list_by_session(self, session_id: int) -> list[Team]:
        rows = self.database.fetchall(
            """
            SELECT * FROM teams
            WHERE session_id = ?
            ORDER BY score DESC, name COLLATE NOCASE ASC, id ASC
            """,
            (session_id,),
        )
        return [self._row_to_team(row) for row in rows]

    def get_by_id(self, team_id: int) -> Team | None:
        row = self.database.fetchone("SELECT * FROM teams WHERE id = ?", (team_id,))
        if row is None:
            return None
        return self._row_to_team(row)

    def update(self, team_id: int, name: str, color: str) -> Team | None:
        self.database.execute(
            "UPDATE teams SET name = ?, color = ? WHERE id = ?",
            (name, color, team_id),
        )
        return self.get_by_id(team_id)

    def update_score(self, team_id: int, score: int) -> Team | None:
        self.database.execute(
            "UPDATE teams SET score = ? WHERE id = ?",
            (score, team_id),
        )
        return self.get_by_id(team_id)

    def reset_scores(self, game_id: int) -> None:
        self.database.execute(
            "UPDATE teams SET score = 0 WHERE game_id = ? AND session_id IS NULL",
            (game_id,),
        )

    def reset_scores_by_session(self, session_id: int) -> None:
        self.database.execute(
            "UPDATE teams SET score = 0 WHERE session_id = ?",
            (session_id,),
        )

    def delete(self, team_id: int) -> None:
        self.database.execute("DELETE FROM teams WHERE id = ?", (team_id,))

    @staticmethod
    def _row_to_team(row) -> Team:
        return Team(
            id=row["id"],
            game_id=row["game_id"],
            session_id=row["session_id"],
            name=row["name"],
            color=row["color"],
            score=row["score"],
            created_at=row["created_at"],
        )

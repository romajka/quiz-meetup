from __future__ import annotations

from datetime import datetime

from quiz_meetup.database.connection import Database
from quiz_meetup.models import ScoreEntry


class ScoreRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def set_question_score(
        self,
        team_id: int,
        round_id: int,
        question_id: int,
        label: str,
        points: int,
    ) -> ScoreEntry | None:
        return self._set_entry(
            team_id=team_id,
            round_id=round_id,
            question_id=question_id,
            entry_type="question",
            label=label,
            points=points,
            lookup_sql=(
                "SELECT id FROM score_entries "
                "WHERE team_id = ? AND question_id = ? AND entry_type = 'question'"
            ),
            lookup_parameters=(team_id, question_id),
        )

    def set_round_adjustment(
        self,
        team_id: int,
        round_id: int,
        label: str,
        points: int,
    ) -> ScoreEntry | None:
        return self._set_entry(
            team_id=team_id,
            round_id=round_id,
            question_id=None,
            entry_type="round_adjustment",
            label=label,
            points=points,
            lookup_sql=(
                "SELECT id FROM score_entries "
                "WHERE team_id = ? AND round_id = ? AND entry_type = 'round_adjustment' AND question_id IS NULL"
            ),
            lookup_parameters=(team_id, round_id),
        )

    def set_total_adjustment(
        self,
        team_id: int,
        label: str,
        points: int,
    ) -> ScoreEntry | None:
        return self._set_entry(
            team_id=team_id,
            round_id=None,
            question_id=None,
            entry_type="total_adjustment",
            label=label,
            points=points,
            lookup_sql=(
                "SELECT id FROM score_entries "
                "WHERE team_id = ? AND entry_type = 'total_adjustment' "
                "AND round_id IS NULL AND question_id IS NULL"
            ),
            lookup_parameters=(team_id,),
        )

    def list_by_team(self, team_id: int) -> list[ScoreEntry]:
        rows = self.database.fetchall(
            """
            SELECT * FROM score_entries
            WHERE team_id = ?
            ORDER BY round_id ASC, question_id ASC, id ASC
            """,
            (team_id,),
        )
        return [self._row_to_entry(row) for row in rows]

    def get_total_by_team(self, team_id: int) -> int:
        row = self.database.fetchone(
            "SELECT COALESCE(SUM(points), 0) AS total_score FROM score_entries WHERE team_id = ?",
            (team_id,),
        )
        return int(row["total_score"]) if row is not None else 0

    def get_base_total_without_manual_total(self, team_id: int) -> int:
        row = self.database.fetchone(
            """
            SELECT COALESCE(SUM(points), 0) AS total_score
            FROM score_entries
            WHERE team_id = ? AND entry_type != 'total_adjustment'
            """,
            (team_id,),
        )
        return int(row["total_score"]) if row is not None else 0

    def get_round_totals_by_game(self, game_id: int) -> dict[tuple[int, int], int]:
        rows = self.database.fetchall(
            """
            SELECT se.team_id, se.round_id, COALESCE(SUM(se.points), 0) AS round_score
            FROM score_entries se
            JOIN teams t ON t.id = se.team_id
            WHERE t.game_id = ? AND t.session_id IS NULL AND se.round_id IS NOT NULL
            GROUP BY se.team_id, se.round_id
            """,
            (game_id,),
        )
        return {
            (int(row["team_id"]), int(row["round_id"])): int(row["round_score"])
            for row in rows
        }

    def get_round_totals_by_session(self, session_id: int) -> dict[tuple[int, int], int]:
        rows = self.database.fetchall(
            """
            SELECT se.team_id, se.round_id, COALESCE(SUM(se.points), 0) AS round_score
            FROM score_entries se
            JOIN teams t ON t.id = se.team_id
            WHERE t.session_id = ? AND se.round_id IS NOT NULL
            GROUP BY se.team_id, se.round_id
            """,
            (session_id,),
        )
        return {
            (int(row["team_id"]), int(row["round_id"])): int(row["round_score"])
            for row in rows
        }

    def reset_game(self, game_id: int) -> None:
        self.database.execute(
            """
            DELETE FROM score_entries
            WHERE team_id IN (SELECT id FROM teams WHERE game_id = ? AND session_id IS NULL)
            """,
            (game_id,),
        )

    def reset_session(self, session_id: int) -> None:
        self.database.execute(
            """
            DELETE FROM score_entries
            WHERE team_id IN (SELECT id FROM teams WHERE session_id = ?)
            """,
            (session_id,),
        )

    def reset_team(self, team_id: int) -> None:
        self.database.execute(
            "DELETE FROM score_entries WHERE team_id = ?",
            (team_id,),
        )

    def _set_entry(
        self,
        team_id: int,
        round_id: int | None,
        question_id: int | None,
        entry_type: str,
        label: str,
        points: int,
        lookup_sql: str,
        lookup_parameters: tuple,
    ) -> ScoreEntry | None:
        existing_row = self.database.fetchone(lookup_sql, lookup_parameters)
        if points == 0:
            if existing_row is not None:
                self.database.execute(
                    "DELETE FROM score_entries WHERE id = ?",
                    (existing_row["id"],),
                )
            return None

        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        if existing_row is None:
            cursor = self.database.execute(
                """
                INSERT INTO score_entries (
                    team_id, round_id, question_id, entry_type, label, points, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (team_id, round_id, question_id, entry_type, label, points, timestamp, timestamp),
            )
            return self.get_by_id(cursor.lastrowid)

        self.database.execute(
            """
            UPDATE score_entries
            SET round_id = ?, question_id = ?, label = ?, points = ?, updated_at = ?
            WHERE id = ?
            """,
            (round_id, question_id, label, points, timestamp, existing_row["id"]),
        )
        return self.get_by_id(existing_row["id"])

    def get_by_id(self, entry_id: int) -> ScoreEntry | None:
        row = self.database.fetchone(
            "SELECT * FROM score_entries WHERE id = ?",
            (entry_id,),
        )
        if row is None:
            return None
        return self._row_to_entry(row)

    @staticmethod
    def _row_to_entry(row) -> ScoreEntry:
        return ScoreEntry(
            id=row["id"],
            team_id=row["team_id"],
            round_id=row["round_id"],
            question_id=row["question_id"],
            entry_type=row["entry_type"],
            label=row["label"],
            points=row["points"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

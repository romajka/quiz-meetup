from __future__ import annotations

from quiz_meetup.database.connection import Database
from quiz_meetup.models import Question


class QuestionRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(
        self,
        round_id: int,
        title: str,
        prompt: str,
        question_type: str,
        notes: str,
        answer: str,
        option_a: str,
        option_b: str,
        option_c: str,
        option_d: str,
        points: int,
        order_index: int,
        timer_seconds: int,
    ) -> Question:
        cursor = self.database.execute(
            """
            INSERT INTO questions (
                round_id, title, prompt, question_type, notes, answer,
                option_a, option_b, option_c, option_d,
                points, order_index, timer_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                round_id,
                title,
                prompt,
                question_type,
                notes,
                answer,
                option_a,
                option_b,
                option_c,
                option_d,
                points,
                order_index,
                timer_seconds,
            ),
        )
        return self.get_by_id(cursor.lastrowid)

    def update(
        self,
        question_id: int,
        title: str,
        prompt: str,
        question_type: str,
        notes: str,
        answer: str,
        option_a: str,
        option_b: str,
        option_c: str,
        option_d: str,
        points: int,
        timer_seconds: int,
    ) -> Question | None:
        self.database.execute(
            """
            UPDATE questions
            SET
                title = ?,
                prompt = ?,
                question_type = ?,
                notes = ?,
                answer = ?,
                option_a = ?,
                option_b = ?,
                option_c = ?,
                option_d = ?,
                points = ?,
                timer_seconds = ?
            WHERE id = ?
            """,
            (
                title,
                prompt,
                question_type,
                notes,
                answer,
                option_a,
                option_b,
                option_c,
                option_d,
                points,
                timer_seconds,
                question_id,
            ),
        )
        return self.get_by_id(question_id)

    def update_order(self, question_id: int, order_index: int) -> None:
        self.database.execute(
            "UPDATE questions SET order_index = ? WHERE id = ?",
            (order_index, question_id),
        )

    def delete(self, question_id: int) -> None:
        self.database.execute("DELETE FROM questions WHERE id = ?", (question_id,))

    def get_next_order_index(self, round_id: int) -> int:
        row = self.database.fetchone(
            "SELECT COALESCE(MAX(order_index), 0) + 1 AS next_index FROM questions WHERE round_id = ?",
            (round_id,),
        )
        return row["next_index"] if row is not None else 1

    def list_by_round(self, round_id: int) -> list[Question]:
        rows = self.database.fetchall(
            """
            SELECT * FROM questions
            WHERE round_id = ?
            ORDER BY order_index ASC, id ASC
            """,
            (round_id,),
        )
        return [self._row_to_question(row) for row in rows]

    def get_by_id(self, question_id: int) -> Question | None:
        row = self.database.fetchone(
            "SELECT * FROM questions WHERE id = ?", (question_id,)
        )
        if row is None:
            return None
        return self._row_to_question(row)

    @staticmethod
    def _row_to_question(row) -> Question:
        return Question(
            id=row["id"],
            round_id=row["round_id"],
            title=row["title"],
            prompt=row["prompt"],
            question_type=row["question_type"],
            notes=row["notes"],
            answer=row["answer"],
            option_a=row["option_a"],
            option_b=row["option_b"],
            option_c=row["option_c"],
            option_d=row["option_d"],
            points=row["points"],
            order_index=row["order_index"],
            timer_seconds=row["timer_seconds"],
        )

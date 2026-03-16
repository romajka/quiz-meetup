from __future__ import annotations

from datetime import datetime

from quiz_meetup.database.connection import Database
from quiz_meetup.models import MediaAsset


class MediaRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(
        self,
        game_id: int | None,
        round_id: int | None,
        question_id: int | None,
        usage_role: str,
        media_type: str,
        title: str,
        original_filename: str,
        file_path: str,
    ) -> MediaAsset:
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        cursor = self.database.execute(
            """
            INSERT INTO media_assets (
                game_id, round_id, question_id, usage_role, media_type, title,
                original_filename, file_path, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                round_id,
                question_id,
                usage_role,
                media_type,
                title,
                original_filename,
                file_path,
                timestamp,
            ),
        )
        return self.get_by_id(cursor.lastrowid)

    def update_metadata(
        self,
        media_id: int,
        title: str,
        usage_role: str,
        round_id: int | None,
        question_id: int | None,
    ) -> MediaAsset | None:
        self.database.execute(
            """
            UPDATE media_assets
            SET title = ?, usage_role = ?, round_id = ?, question_id = ?
            WHERE id = ?
            """,
            (title, usage_role, round_id, question_id, media_id),
        )
        return self.get_by_id(media_id)

    def list_by_game(self, game_id: int) -> list[MediaAsset]:
        rows = self.database.fetchall(
            """
            SELECT * FROM media_assets
            WHERE game_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (game_id,),
        )
        return [self._row_to_media(row) for row in rows]

    def delete(self, media_id: int) -> None:
        self.database.execute("DELETE FROM media_assets WHERE id = ?", (media_id,))

    def get_by_id(self, media_id: int) -> MediaAsset | None:
        row = self.database.fetchone(
            "SELECT * FROM media_assets WHERE id = ?",
            (media_id,),
        )
        if row is None:
            return None
        return self._row_to_media(row)

    def delete_by_game(self, game_id: int) -> None:
        self.database.execute(
            "DELETE FROM media_assets WHERE game_id = ?",
            (game_id,),
        )

    @staticmethod
    def _row_to_media(row) -> MediaAsset:
        return MediaAsset(
            id=row["id"],
            game_id=row["game_id"],
            round_id=row["round_id"],
            question_id=row["question_id"],
            usage_role=row["usage_role"],
            media_type=row["media_type"],
            title=row["title"],
            original_filename=row["original_filename"],
            file_path=row["file_path"],
            created_at=row["created_at"],
        )

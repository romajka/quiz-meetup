from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MediaAsset:
    id: int
    game_id: int | None
    round_id: int | None
    question_id: int | None
    usage_role: str
    media_type: str
    title: str
    original_filename: str
    file_path: str
    created_at: str

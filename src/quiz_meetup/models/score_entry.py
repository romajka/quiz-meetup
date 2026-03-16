from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ScoreEntry:
    id: int
    team_id: int
    round_id: int | None
    question_id: int | None
    entry_type: str
    label: str
    points: int
    created_at: str
    updated_at: str

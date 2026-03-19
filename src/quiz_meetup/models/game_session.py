from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GameSession:
    id: int
    game_id: int
    session_number: int
    status: str
    completed_round_ids: str
    active_round_id: int | None
    active_question_id: int | None
    display_phase: str
    started_at: str
    updated_at: str
    finished_at: str | None

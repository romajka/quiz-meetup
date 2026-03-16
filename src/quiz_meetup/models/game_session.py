from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GameSession:
    id: int
    game_id: int
    session_number: int
    status: str
    completed_round_ids: str
    started_at: str
    updated_at: str
    finished_at: str | None


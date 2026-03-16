from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Team:
    id: int
    game_id: int
    session_id: int | None
    name: str
    color: str
    score: int
    created_at: str

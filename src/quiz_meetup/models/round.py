from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Round:
    id: int
    game_id: int
    title: str
    order_index: int
    timer_seconds: int
    notes: str

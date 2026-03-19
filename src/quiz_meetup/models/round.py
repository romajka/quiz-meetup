from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Round:
    id: int
    game_id: int
    title: str
    round_type: str
    order_index: int
    timer_seconds: int
    settings_text: str
    notes: str

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Game:
    id: int
    title: str
    description: str
    created_at: str
    updated_at: str

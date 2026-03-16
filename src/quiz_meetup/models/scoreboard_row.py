from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ScoreboardRow:
    team_id: int
    team_name: str
    team_color: str
    total_score: int
    round_scores: dict[int, int] = field(default_factory=dict)

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Question:
    id: int
    round_id: int
    title: str
    prompt: str
    question_type: str
    notes: str
    answer: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    points: int
    order_index: int
    timer_seconds: int

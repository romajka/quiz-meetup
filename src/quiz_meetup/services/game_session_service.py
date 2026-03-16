from __future__ import annotations

from quiz_meetup.models import GameSession
from quiz_meetup.repositories import GameSessionRepository


class GameSessionService:
    def __init__(self, repository: GameSessionRepository) -> None:
        self.repository = repository

    def start_new_session(self, game_id: int) -> GameSession:
        return self.repository.create(game_id)

    def list_sessions_by_game(self, game_id: int) -> list[GameSession]:
        return self.repository.list_by_game(game_id)

    def get_session(self, session_id: int) -> GameSession | None:
        return self.repository.get_by_id(session_id)

    def get_active_session(self, game_id: int) -> GameSession | None:
        return self.repository.get_active_by_game(game_id)

    def touch_session(self, session_id: int) -> GameSession | None:
        return self.repository.touch(session_id)

    def get_completed_round_ids(self, session_id: int) -> set[int]:
        session = self.repository.get_by_id(session_id)
        if session is None or not session.completed_round_ids.strip():
            return set()
        return {
            int(raw_id)
            for raw_id in session.completed_round_ids.split(",")
            if raw_id.strip().isdigit()
        }

    def mark_round_completed(self, session_id: int, round_id: int) -> GameSession | None:
        completed_round_ids = self.get_completed_round_ids(session_id)
        completed_round_ids.add(round_id)
        return self.repository.set_completed_round_ids(session_id, sorted(completed_round_ids))

    def finish_session(self, session_id: int) -> GameSession | None:
        return self.repository.finish(session_id)


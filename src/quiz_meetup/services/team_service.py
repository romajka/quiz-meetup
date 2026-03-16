from __future__ import annotations

from quiz_meetup.config import DEFAULT_TEAM_COLOR
from quiz_meetup.models import Team
from quiz_meetup.repositories import TeamRepository


class TeamService:
    def __init__(self, repository: TeamRepository) -> None:
        self.repository = repository

    def create_team(
        self,
        game_id: int,
        name: str,
        color: str | None = None,
        session_id: int | None = None,
    ) -> Team:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Название команды не может быть пустым.")
        normalized_color = (color or DEFAULT_TEAM_COLOR).strip() or DEFAULT_TEAM_COLOR
        return self.repository.create(game_id, normalized_name, normalized_color, session_id)

    def list_teams_by_game(self, game_id: int) -> list[Team]:
        return self.repository.list_by_game(game_id)

    def list_teams_by_session(self, session_id: int) -> list[Team]:
        return self.repository.list_by_session(session_id)

    def get_team(self, team_id: int) -> Team | None:
        return self.repository.get_by_id(team_id)

    def update_team(self, team_id: int, name: str, color: str | None = None) -> Team:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Название команды не может быть пустым.")
        normalized_color = (color or DEFAULT_TEAM_COLOR).strip() or DEFAULT_TEAM_COLOR
        updated_team = self.repository.update(team_id, normalized_name, normalized_color)
        if updated_team is None:
            raise ValueError("Команда не найдена.")
        return updated_team

    def delete_team(self, team_id: int) -> None:
        team = self.repository.get_by_id(team_id)
        if team is None:
            raise ValueError("Команда не найдена.")
        self.repository.delete(team_id)

from __future__ import annotations

from quiz_meetup.models import Game
from quiz_meetup.repositories import (
    GameRepository,
    QuestionRepository,
    RoundRepository,
    TeamRepository,
)
from quiz_meetup.services.media_service import MediaService


class GameService:
    def __init__(
        self,
        repository: GameRepository,
        round_repository: RoundRepository,
        question_repository: QuestionRepository,
        team_repository: TeamRepository,
        media_service: MediaService,
    ) -> None:
        self.repository = repository
        self.round_repository = round_repository
        self.question_repository = question_repository
        self.team_repository = team_repository
        self.media_service = media_service

    def create_game(self, title: str, description: str) -> Game:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Название игры не может быть пустым.")
        return self.repository.create(normalized_title, description.strip())

    def update_game(self, game_id: int, title: str, description: str) -> Game:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Название игры не может быть пустым.")

        updated_game = self.repository.update(game_id, normalized_title, description.strip())
        if updated_game is None:
            raise ValueError("Игра не найдена.")
        return updated_game

    def delete_game(self, game_id: int) -> None:
        game = self.repository.get_by_id(game_id)
        if game is None:
            raise ValueError("Игра не найдена.")

        self.media_service.remove_game_media(game_id)
        self.repository.delete(game_id)

    def duplicate_game(self, game_id: int) -> Game:
        source_game = self.repository.get_by_id(game_id)
        if source_game is None:
            raise ValueError("Игра не найдена.")

        copied_game = self.repository.create(
            title=f"{source_game.title} (копия)",
            description=source_game.description,
        )

        round_id_map: dict[int, int] = {}
        question_id_map: dict[int, int] = {}

        for round_item in self.round_repository.list_by_game(source_game.id):
            copied_round = self.round_repository.create(
                game_id=copied_game.id,
                title=round_item.title,
                round_type=round_item.round_type,
                order_index=round_item.order_index,
                timer_seconds=round_item.timer_seconds,
                settings_text=round_item.settings_text,
                notes=round_item.notes,
            )
            round_id_map[round_item.id] = copied_round.id

            for question in self.question_repository.list_by_round(round_item.id):
                copied_question = self.question_repository.create(
                    round_id=copied_round.id,
                    title=question.title,
                    prompt=question.prompt,
                    question_type=question.question_type,
                    notes=question.notes,
                    answer=question.answer,
                    option_a=question.option_a,
                    option_b=question.option_b,
                    option_c=question.option_c,
                    option_d=question.option_d,
                    points=question.points,
                    order_index=question.order_index,
                    timer_seconds=question.timer_seconds,
                )
                question_id_map[question.id] = copied_question.id

        for team in self.team_repository.list_by_game(source_game.id):
            self.team_repository.create(
                game_id=copied_game.id,
                name=team.name,
                color=team.color,
            )

        self.media_service.clone_media_assets(
            source_game_id=source_game.id,
            target_game_id=copied_game.id,
            round_id_map=round_id_map,
            question_id_map=question_id_map,
        )

        return copied_game

    def list_games(self) -> list[Game]:
        return self.repository.list_all()

    def get_game(self, game_id: int) -> Game | None:
        return self.repository.get_by_id(game_id)

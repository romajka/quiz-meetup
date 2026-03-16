from __future__ import annotations

from quiz_meetup.models import Question, ScoreboardRow, Team
from quiz_meetup.repositories import QuestionRepository, RoundRepository, ScoreRepository, TeamRepository


class ScoreService:
    def __init__(
        self,
        team_repository: TeamRepository,
        score_repository: ScoreRepository,
        round_repository: RoundRepository,
        question_repository: QuestionRepository,
    ) -> None:
        self.team_repository = team_repository
        self.score_repository = score_repository
        self.round_repository = round_repository
        self.question_repository = question_repository

    def change_score(self, team_id: int, delta: int) -> Team:
        team = self._require_team(team_id)
        target_total = team.score + delta
        return self.set_total_score(team_id, target_total)

    def award_question_score(self, team_id: int, question_id: int) -> Team:
        question = self._require_question(question_id)
        return self.set_question_score(team_id, question_id, question.points)

    def set_question_score(self, team_id: int, question_id: int, points: int) -> Team:
        if points < 0:
            raise ValueError("Очки за вопрос не могут быть отрицательными.")
        self._require_team(team_id)
        question = self._require_question(question_id)
        self.score_repository.set_question_score(
            team_id=team_id,
            round_id=question.round_id,
            question_id=question.id,
            label=question.title,
            points=points,
        )
        return self._sync_team_score(team_id)

    def set_round_adjustment(self, team_id: int, round_id: int, points: int) -> Team:
        self._require_team(team_id)
        round_item = self.round_repository.get_by_id(round_id)
        if round_item is None:
            raise ValueError("Раунд не найден.")
        self.score_repository.set_round_adjustment(
            team_id=team_id,
            round_id=round_id,
            label=f"Корректировка раунда: {round_item.title}",
            points=points,
        )
        return self._sync_team_score(team_id)

    def set_round_total(self, team_id: int, round_id: int, total_score: int) -> Team:
        if total_score < 0:
            raise ValueError("Счёт раунда не может быть отрицательным.")
        self._require_team(team_id)
        round_item = self.round_repository.get_by_id(round_id)
        if round_item is None:
            raise ValueError("Раунд не найден.")

        base_total = 0
        for entry in self.score_repository.list_by_team(team_id):
            if entry.round_id != round_id:
                continue
            if entry.entry_type == "round_adjustment":
                continue
            base_total += entry.points

        adjustment = total_score - base_total
        self.score_repository.set_round_adjustment(
            team_id=team_id,
            round_id=round_id,
            label=f"Корректировка раунда: {round_item.title}",
            points=adjustment,
        )
        return self._sync_team_score(team_id)

    def set_total_score(self, team_id: int, total_score: int) -> Team:
        if total_score < 0:
            raise ValueError("Итоговый счёт не может быть отрицательным.")
        self._require_team(team_id)
        base_total = self.score_repository.get_base_total_without_manual_total(team_id)
        adjustment = total_score - base_total
        self.score_repository.set_total_adjustment(
            team_id=team_id,
            label="Ручная корректировка общего счёта",
            points=adjustment,
        )
        return self._sync_team_score(team_id)

    def reset_scores(self, game_id: int) -> None:
        self.score_repository.reset_game(game_id)
        self.team_repository.reset_scores(game_id)

    def reset_scores_for_session(self, session_id: int) -> None:
        self.score_repository.reset_session(session_id)
        self.team_repository.reset_scores_by_session(session_id)

    def reset_team_scores(self, team_id: int) -> Team:
        self.score_repository.reset_team(team_id)
        updated_team = self.team_repository.update_score(team_id, 0)
        if updated_team is None:
            raise ValueError("Команда не найдена.")
        return updated_team

    def get_scoreboard(self, game_id: int) -> list[Team]:
        return self.team_repository.list_by_game(game_id)

    def get_scoreboard_rows(self, game_id: int) -> list[ScoreboardRow]:
        teams = self.team_repository.list_by_game(game_id)
        rounds = self.round_repository.list_by_game(game_id)
        round_totals = self.score_repository.get_round_totals_by_game(game_id)
        rows: list[ScoreboardRow] = []
        for team in teams:
            round_scores: dict[int, int] = {}
            for round_item in rounds:
                round_scores[round_item.id] = round_totals.get((team.id, round_item.id), 0)
            rows.append(
                ScoreboardRow(
                    team_id=team.id,
                    team_name=team.name,
                    team_color=team.color,
                    total_score=team.score,
                    round_scores=round_scores,
                )
            )
        rows.sort(key=lambda row: (-row.total_score, row.team_name.lower(), row.team_id))
        return rows

    def get_scoreboard_rows_for_session(self, session_id: int, game_id: int) -> list[ScoreboardRow]:
        teams = self.team_repository.list_by_session(session_id)
        rounds = self.round_repository.list_by_game(game_id)
        round_totals = self.score_repository.get_round_totals_by_session(session_id)
        rows: list[ScoreboardRow] = []
        for team in teams:
            round_scores: dict[int, int] = {}
            for round_item in rounds:
                round_scores[round_item.id] = round_totals.get((team.id, round_item.id), 0)
            rows.append(
                ScoreboardRow(
                    team_id=team.id,
                    team_name=team.name,
                    team_color=team.color,
                    total_score=team.score,
                    round_scores=round_scores,
                )
            )
        rows.sort(key=lambda row: (-row.total_score, row.team_name.lower(), row.team_id))
        return rows

    def get_winner_places(self, game_id: int) -> list[tuple[int, Team]]:
        teams = self.team_repository.list_by_game(game_id)
        if not teams:
            return []
        return [(index, team) for index, team in enumerate(teams[:5], start=1)]

    def get_winner_places_for_session(self, session_id: int) -> list[tuple[int, Team]]:
        teams = self.team_repository.list_by_session(session_id)
        if not teams:
            return []
        return [(index, team) for index, team in enumerate(teams[:5], start=1)]

    def _sync_team_score(self, team_id: int) -> Team:
        total_score = self.score_repository.get_total_by_team(team_id)
        updated_team = self.team_repository.update_score(team_id, total_score)
        if updated_team is None:
            raise ValueError("Команда не найдена.")
        return updated_team

    def _require_team(self, team_id: int) -> Team:
        team = self.team_repository.get_by_id(team_id)
        if team is None:
            raise ValueError("Команда не найдена.")
        return team

    def _require_question(self, question_id: int) -> Question:
        question = self.question_repository.get_by_id(question_id)
        if question is None:
            raise ValueError("Вопрос не найден.")
        return question

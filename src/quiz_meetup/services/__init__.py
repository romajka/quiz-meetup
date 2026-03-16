from __future__ import annotations

from dataclasses import dataclass

from quiz_meetup.services.game_service import GameService
from quiz_meetup.services.game_session_service import GameSessionService
from quiz_meetup.services.media_service import MediaService
from quiz_meetup.services.presentation_service import PresentationService
from quiz_meetup.services.question_service import QuestionService
from quiz_meetup.services.round_service import RoundService
from quiz_meetup.services.score_service import ScoreService
from quiz_meetup.services.settings_service import SettingsService
from quiz_meetup.services.team_service import TeamService
from quiz_meetup.services.timer_service import TimerService


@dataclass(slots=True)
class ServiceRegistry:
    game_service: GameService
    game_session_service: GameSessionService
    round_service: RoundService
    question_service: QuestionService
    media_service: MediaService
    team_service: TeamService
    score_service: ScoreService
    timer_service: TimerService
    presentation_service: PresentationService
    settings_service: SettingsService


__all__ = [
    "GameService",
    "GameSessionService",
    "RoundService",
    "QuestionService",
    "MediaService",
    "TeamService",
    "ScoreService",
    "TimerService",
    "PresentationService",
    "SettingsService",
    "ServiceRegistry",
]

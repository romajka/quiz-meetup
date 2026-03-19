from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from quiz_meetup.config import APP_NAME
from quiz_meetup.database import Database, initialize_database
from quiz_meetup.paths import ApplicationPaths, build_application_paths
from quiz_meetup.repositories import (
    GameRepository,
    GameSessionRepository,
    MediaRepository,
    QuestionRepository,
    RoundRepository,
    ScoreRepository,
    SettingsRepository,
    TeamRepository,
)
from quiz_meetup.services import (
    GameService,
    GameSessionService,
    MediaService,
    PresentationService,
    QuestionService,
    RoundService,
    ScoreService,
    ServiceRegistry,
    SettingsService,
    TeamService,
    TimerService,
)
from quiz_meetup.ui.icons import interface_icon
from quiz_meetup.ui.main_window import MainWindow
from quiz_meetup.ui.styles import apply_application_style


def build_services(database: Database, paths: ApplicationPaths) -> ServiceRegistry:
    game_repository = GameRepository(database)
    game_session_repository = GameSessionRepository(database)
    round_repository = RoundRepository(database)
    question_repository = QuestionRepository(database)
    media_repository = MediaRepository(database)
    team_repository = TeamRepository(database)
    score_repository = ScoreRepository(database)
    settings_repository = SettingsRepository(database)

    media_service = MediaService(media_repository, paths)
    presentation_service = PresentationService()
    timer_service = TimerService()
    timer_service.state_changed.connect(presentation_service.set_timer_state)
    presentation_service.set_timer_state(timer_service.state)

    return ServiceRegistry(
        game_service=GameService(
            repository=game_repository,
            round_repository=round_repository,
            question_repository=question_repository,
            team_repository=team_repository,
            media_service=media_service,
        ),
        game_session_service=GameSessionService(game_session_repository),
        round_service=RoundService(round_repository),
        question_service=QuestionService(question_repository),
        media_service=media_service,
        team_service=TeamService(team_repository),
        score_service=ScoreService(
            team_repository=team_repository,
            score_repository=score_repository,
            round_repository=round_repository,
            question_repository=question_repository,
        ),
        timer_service=timer_service,
        presentation_service=presentation_service,
        settings_service=SettingsService(settings_repository),
    )


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setWindowIcon(interface_icon("Command", color="#10213a", size=24))
    apply_application_style(application)

    paths = build_application_paths()
    database = Database(paths.database_path)
    initialize_database(database)
    application.aboutToQuit.connect(database.close)

    services = build_services(database, paths)
    window = MainWindow(
        services=services,
        database_path=paths.database_path,
        app_data_dir=paths.app_data_dir,
        media_dir=paths.media_dir,
    )
    window.show()
    QTimer.singleShot(0, window.showMaximized)

    return application.exec()

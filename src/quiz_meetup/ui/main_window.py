from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from quiz_meetup.models import Game
from quiz_meetup.services import ServiceRegistry
from quiz_meetup.ui.icons import apply_button_icon, interface_icon
from quiz_meetup.ui.pages.control_page import GameControlPage
from quiz_meetup.ui.pages.games_page import GamesPage
from quiz_meetup.ui.pages.media_page import MediaPage
from quiz_meetup.ui.pages.questions_page import QuestionsPage
from quiz_meetup.ui.pages.rounds_page import RoundsPage
from quiz_meetup.ui.pages.scores_page import ScoresPage
from quiz_meetup.ui.pages.settings_page import SettingsPage
from quiz_meetup.ui.pages.teams_page import TeamsPage
from quiz_meetup.ui.projector_window import ProjectorWindow


class MainWindow(QMainWindow):
    def __init__(
        self,
        services: ServiceRegistry,
        database_path: Path,
        app_data_dir: Path,
        media_dir: Path,
    ) -> None:
        super().__init__()
        self.services = services
        self.database_path = database_path
        self.app_data_dir = app_data_dir
        self.media_dir = media_dir
        self.projector_window: ProjectorWindow | None = None
        self.running_game_id: int | None = None
        self.running_session_id: int | None = None
        self.completed_round_ids: set[int] = set()
        self.section_buttons: list[QPushButton] = []
        self.section_definitions: list[tuple[str, str, QWidget]] = []

        self.setWindowTitle("Quiz Meetup")
        self.setWindowIcon(interface_icon("Command", color="#10213a", size=24))
        self.setWindowFlag(Qt.Window, True)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self.setMinimumSize(920, 640)
        self.resize(1600, 960)

        self.games_page = GamesPage(
            game_service=self.services.game_service,
            game_session_service=self.services.game_session_service,
            round_service=self.services.round_service,
            question_service=self.services.question_service,
            media_service=self.services.media_service,
            team_service=self.services.team_service,
        )
        self.rounds_page = RoundsPage(
            game_service=self.services.game_service,
            round_service=self.services.round_service,
        )
        self.questions_page = QuestionsPage(
            game_service=self.services.game_service,
            round_service=self.services.round_service,
            question_service=self.services.question_service,
            media_service=self.services.media_service,
        )
        self.media_page = MediaPage(
            game_service=self.services.game_service,
            media_service=self.services.media_service,
            round_service=self.services.round_service,
            question_service=self.services.question_service,
        )
        self.teams_page = TeamsPage(
            game_service=self.services.game_service,
            team_service=self.services.team_service,
        )
        self.scores_page = ScoresPage(
            game_service=self.services.game_service,
            round_service=self.services.round_service,
            question_service=self.services.question_service,
            score_service=self.services.score_service,
            team_service=self.services.team_service,
        )
        self.game_control_page = GameControlPage()
        self.settings_page = SettingsPage(
            settings_service=self.services.settings_service,
            app_data_dir=self.app_data_dir,
            database_path=self.database_path,
            media_dir=self.media_dir,
        )

        self.page_stack = QStackedWidget()
        self.section_title_label = QLabel()
        self.section_title_label.setObjectName("PageTitle")
        self.section_description_label = QLabel()
        self.section_description_label.setObjectName("PageHint")
        self.section_description_label.setWordWrap(True)
        self.active_game_badge = QLabel("Активная игра: не выбрана")
        self.active_game_badge.setObjectName("StatusBadge")
        self.autosave_badge = QLabel("Автосохранение: ждёт изменений")
        self.autosave_badge.setObjectName("AutosaveBadge")

        self.quick_new_game_button = QPushButton("Создать игру")
        self.quick_new_game_button.setObjectName("AccentButton")
        self.quick_projector_button = QPushButton("Открыть экран проектора")
        self.quick_projector_button.setObjectName("SecondaryButton")
        self.quick_fullscreen_button = QPushButton("Развернуть окно")
        self.quick_fullscreen_button.setObjectName("SecondaryButton")
        self.hotkey_shortcuts: list[QShortcut] = []

        self._configure_sections()
        self._build_ui()
        self._apply_icons()
        self._connect_signals()
        self._build_hotkeys()

        self.refresh_all_pages()
        self.set_section(0)
        self.show_welcome_screen()
        self.statusBar().showMessage(f"База данных: {self.database_path}")

    def _configure_sections(self) -> None:
        self.section_definitions = [
            ("Игры", "Первый экран программы: список игр, создание, открытие, копия и запуск.", self.games_page),
            ("Раунды", "Подготовка структуры игры и порядка раундов.", self.rounds_page),
            ("Вопросы", "Подготовка вопросов, ответов, медиа и таймера.", self.questions_page),
            ("Медиа", "Общие файлы игры, а также изображения, аудио и видео для вопросов.", self.media_page),
            ("Команды", "Список команд выбранной игры.", self.teams_page),
            ("Таблица очков", "Ручное начисление баллов по раундам и итоговая таблица.", self.scores_page),
            ("Панель ведущего", "Отдельный режим проведения игры и управления проектором.", self.game_control_page),
            ("Настройки", "Базовые параметры приложения и локального хранения.", self.settings_page),
        ]

        for _, _, page in self.section_definitions:
            self.page_stack.addWidget(page)

    def _build_ui(self) -> None:
        container = QWidget()
        root_layout = QHBoxLayout(container)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(18)

        sidebar = QFrame()
        sidebar.setObjectName("SidebarCard")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(10)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_badge = QLabel()
        brand_badge.setObjectName("BrandBadge")
        brand_badge.setFixedSize(44, 44)
        brand_badge.setPixmap(interface_icon("Command", color="#ffffff", size=20).pixmap(20, 20))
        brand_badge.setAlignment(Qt.AlignCenter)

        brand_text_layout = QVBoxLayout()
        brand_text_layout.setSpacing(2)
        app_title = QLabel("Quiz Meetup")
        app_title.setObjectName("HeaderTitle")
        app_title.setWordWrap(True)
        app_subtitle = QLabel("Панель ведущего")
        app_subtitle.setObjectName("HeaderSubtitle")

        brand_text_layout.addWidget(app_title)
        brand_text_layout.addWidget(app_subtitle)
        brand_row.addWidget(brand_badge)
        brand_row.addLayout(brand_text_layout, 1)

        sidebar_layout.addLayout(brand_row)
        sidebar_layout.addSpacing(10)

        for index, (title, _, _) in enumerate(self.section_definitions):
            button = QPushButton(title)
            button.setObjectName("SectionButton")
            button.setCheckable(True)
            button.setMinimumHeight(56)
            button.clicked.connect(lambda checked=False, idx=index: self.set_section(idx))
            self.section_buttons.append(button)
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch(1)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(16)

        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(18, 18, 18, 18)
        header_layout.setSpacing(16)

        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(6)
        header_text_layout.addWidget(self.section_title_label)
        header_text_layout.addWidget(self.section_description_label)
        header_text_layout.addWidget(self.active_game_badge)
        header_text_layout.addWidget(self.autosave_badge)

        header_actions_layout = QVBoxLayout()
        header_actions_layout.setSpacing(10)
        self.quick_new_game_button.setMinimumHeight(48)
        self.quick_projector_button.setMinimumHeight(48)
        self.quick_fullscreen_button.setMinimumHeight(48)
        header_actions_layout.addWidget(self.quick_new_game_button)
        header_actions_layout.addWidget(self.quick_projector_button)
        header_actions_layout.addWidget(self.quick_fullscreen_button)
        header_actions_layout.addStretch(1)

        header_layout.addLayout(header_text_layout, 1)
        header_layout.addLayout(header_actions_layout)

        content_layout.addWidget(header_card)
        content_layout.addWidget(self.page_stack, 1)

        root_layout.addWidget(sidebar)
        root_layout.addLayout(content_layout, 1)

        self.setCentralWidget(container)

    def _apply_icons(self) -> None:
        sidebar_icon_map = {
            "Игры": "Command",
            "Раунды": "Book_Open",
            "Вопросы": "Search_Magnifying_Glass",
            "Медиа": "External_Link",
            "Команды": "Main_Component",
            "Таблица очков": "Chart_Bar_Vertical_01",
            "Панель ведущего": "Settings_Future",
            "Настройки": "Settings",
        }
        for button in self.section_buttons:
            icon_name = sidebar_icon_map.get(button.text())
            if icon_name:
                apply_button_icon(button, icon_name, color="#f8fafc", size=18)

        apply_button_icon(self.quick_new_game_button, "Check_Big", color="#ffffff", size=18)
        apply_button_icon(self.quick_projector_button, "External_Link", color="#173b86", size=18)
        apply_button_icon(self.quick_fullscreen_button, "External_Link", color="#2c3442", size=18)

    def _connect_signals(self) -> None:
        self.quick_new_game_button.clicked.connect(lambda _checked=False: self.open_new_game_editor())
        self.quick_projector_button.clicked.connect(
            lambda _checked=False: self.open_projector_window()
        )
        self.quick_fullscreen_button.clicked.connect(self.toggle_maximized)

        self.games_page.data_changed.connect(self.refresh_all_pages)
        self.games_page.autosave_status_changed.connect(self._set_autosave_status)
        self.games_page.open_media_requested.connect(self.open_media_page_for_current_game)
        self.games_page.edit_round_requested.connect(self.open_round_editor_from_games)
        self.games_page.edit_question_requested.connect(self.open_question_editor_from_games)
        self.games_page.view_changed.connect(self.refresh_context_panels)
        self.games_page.start_game_requested.connect(self.start_game_session)
        self.games_page.start_new_session_requested.connect(self.start_new_session)
        self.games_page.continue_session_requested.connect(self.continue_session)
        self.rounds_page.data_changed.connect(self.refresh_all_pages)
        self.questions_page.data_changed.connect(self.refresh_all_pages)
        self.media_page.data_changed.connect(self.refresh_all_pages)
        self.teams_page.data_changed.connect(self.refresh_all_pages)
        self.scores_page.data_changed.connect(self.refresh_all_pages)
        self.settings_page.data_changed.connect(self.handle_settings_changed)

        self.games_page.selection_changed.connect(self.refresh_context_panels)

        self.game_control_page.open_projector_requested.connect(self.open_projector_window)
        self.game_control_page.show_splash_requested.connect(
            lambda: self.show_welcome_screen(open_window=True)
        )
        self.game_control_page.show_qr_requested.connect(self.show_connection_code_screen)
        self.game_control_page.show_score_column_requested.connect(self.show_score_column)
        self.game_control_page.hide_score_column_requested.connect(self.show_waiting_screen)
        self.game_control_page.hide_scores_requested.connect(self.show_waiting_screen)
        self.game_control_page.start_timer_requested.connect(self.start_timer)
        self.game_control_page.pause_timer_requested.connect(self.pause_timer)
        self.game_control_page.resume_timer_requested.connect(self.resume_timer)
        self.game_control_page.reset_timer_requested.connect(self.reset_timer)
        self.game_control_page.play_sponsor_requested.connect(self.show_partner_block)
        self.game_control_page.play_background_music_requested.connect(
            self.play_background_music
        )
        self.game_control_page.stop_background_music_requested.connect(
            self.stop_background_music
        )
        self.game_control_page.show_waiting_requested.connect(self.show_waiting_screen)
        self.game_control_page.show_round_requested.connect(self.show_selected_round)
        self.game_control_page.show_question_requested.connect(self.show_selected_question)
        self.game_control_page.hide_question_requested.connect(self.hide_question_screen)
        self.game_control_page.show_answer_requested.connect(self.show_answer_screen)
        self.game_control_page.show_scores_requested.connect(self.show_scoreboard)
        self.game_control_page.show_teams_requested.connect(self.show_teams_screen)
        self.game_control_page.show_winners_requested.connect(self.show_winners_screen)
        self.game_control_page.next_question_requested.connect(self.show_next_question)
        self.game_control_page.previous_question_requested.connect(
            self.show_previous_question
        )
        self.game_control_page.show_media_requested.connect(self.show_game_media_asset)
        self.game_control_page.select_round_by_id_requested.connect(self.select_round_in_control_panel)
        self.game_control_page.show_round_by_id_requested.connect(self.show_round_by_id)
        self.game_control_page.show_question_by_id_requested.connect(self.show_question_by_id)
        self.game_control_page.show_answer_by_id_requested.connect(self.show_answer_by_id)
        self.game_control_page.start_timer_for_question_requested.connect(
            self.start_timer_for_question
        )
        self.game_control_page.pause_timer_for_question_requested.connect(
            self.pause_timer_for_question
        )
        self.game_control_page.reset_timer_for_question_requested.connect(
            self.reset_timer_for_question
        )
        self.game_control_page.stop_answers_for_question_requested.connect(
            self.stop_answers_for_question
        )
        self.game_control_page.show_question_media_by_id_requested.connect(
            self.show_question_media_by_id
        )
        self.game_control_page.show_answer_media_by_id_requested.connect(
            self.show_answer_media_by_id
        )
        self.game_control_page.finish_round_requested.connect(self.finish_current_round)
        self.services.presentation_service.state_changed.connect(
            lambda _state: self.refresh_context_panels()
        )

    def refresh_all_pages(self) -> None:
        self.games_page.refresh()
        self.rounds_page.refresh()
        self.questions_page.refresh()
        self.media_page.refresh()
        self.teams_page.refresh()
        self.scores_page.refresh()
        self.settings_page.refresh()
        self.refresh_context_panels()

    def handle_settings_changed(self) -> None:
        self.settings_page.refresh()
        self.refresh_context_panels()
        self.show_welcome_screen()

    def refresh_context_panels(self) -> None:
        game = self._resolve_active_game()
        round_item = self._resolve_active_round()
        question = self._resolve_active_question()
        scene = self.services.presentation_service.state.scene
        projector_title = self.services.presentation_service.state.title
        timer_state = self.services.timer_service.state

        round_questions = (
            self.services.question_service.list_questions_by_round(round_item.id)
            if round_item is not None
            else []
        )
        self.game_control_page.update_context(
            game,
            round_item,
            question,
            scene,
            projector_title,
            self.services.presentation_service.state.music_status,
            timer_state.display_text if timer_state.total_seconds > 0 else "--:--",
            timer_state.source_label or "Таймер не подготовлен",
            timer_state.status_label,
        )
        rounds = self.services.round_service.list_rounds_by_game(game.id) if game is not None else []
        media_assets = self.services.media_service.list_media_by_game(game.id) if game is not None else []
        self.game_control_page.update_dashboard(
            game=game,
            rounds=rounds,
            media_assets=media_assets,
            selected_round=round_item,
            round_questions=round_questions,
            current_question=question,
            round_completed=bool(round_item is not None and round_item.id in self.completed_round_ids),
        )
        live_game = self._get_running_game()
        if live_game is not None:
            if self.running_session_id is not None:
                session = self.services.game_session_service.get_session(self.running_session_id)
                if session is not None:
                    self.active_game_badge.setText(
                        f"Игра в эфире: {live_game.title} · Запуск #{session.session_number}"
                    )
                else:
                    self.active_game_badge.setText(f"Игра в эфире: {live_game.title}")
            else:
                self.active_game_badge.setText(f"Игра в эфире: {live_game.title}")
        else:
            self.active_game_badge.setText(
                f"Активная игра: {game.title}" if game is not None else "Активная игра: не выбрана"
            )
        self._update_header_context()

    def set_section(self, index: int) -> None:
        current_index = self.page_stack.currentIndex()
        if current_index != index and self.page_stack.currentWidget() is self.games_page:
            self.games_page.flush_autosave()

        self.page_stack.setCurrentIndex(index)
        _, _, page = self.section_definitions[index]
        refresh_method = getattr(page, "refresh", None)
        if callable(refresh_method):
            refresh_method()
        for button_index, button in enumerate(self.section_buttons):
            button.setChecked(button_index == index)

        self._update_hotkey_states()
        self.refresh_context_panels()

    def open_new_game_editor(self) -> None:
        self.set_section(0)
        self.games_page.start_new_game()
        self.games_page.title_input.setFocus()

    def start_game_session(self, game_id: int) -> None:
        self.start_new_session(game_id)

    def start_new_session(self, game_id: int) -> None:
        game = self.services.game_service.get_game(game_id)
        if game is None:
            self._show_warning("Выбранная игра не найдена.")
            return

        session = self.services.game_session_service.start_new_session(game.id)
        self.running_game_id = game.id
        self.running_session_id = session.id
        self.completed_round_ids = set()
        self._apply_live_session_context(game.id, session.id)
        self._update_session_live_state(display_phase="waiting", round_id=None, question_id=None)
        rounds = self.services.round_service.list_rounds_by_game(game.id)
        if rounds and self.games_page.get_selected_round() is None and hasattr(self.games_page, "_select_round"):
            self.games_page._select_round(rounds[0].id)
        self.set_section(6)
        self.refresh_context_panels()

    def continue_session(self, session_id: int) -> None:
        session = self.services.game_session_service.touch_session(session_id)
        if session is None:
            self._show_warning("Сессия игры не найдена.")
            return

        game = self.services.game_service.get_game(session.game_id)
        if game is None:
            self._show_warning("Игра для выбранной сессии не найдена.")
            return

        self.running_game_id = game.id
        self.running_session_id = session.id
        self.completed_round_ids = self.services.game_session_service.get_completed_round_ids(session.id)
        self._apply_live_session_context(game.id, session.id)
        self._restore_live_session_state(session)
        self.set_section(6)
        self.refresh_context_panels()
        self._resume_session_presentation(session)

    def open_media_page_for_current_game(self) -> None:
        game = self.games_page.get_selected_game()
        self.set_section(3)
        if game is not None:
            self.media_page.set_current_game(game.id)

    def open_round_editor_from_games(self, round_id: int) -> None:
        self.set_section(1)
        self.rounds_page.open_round(round_id)
        self.refresh_context_panels()

    def open_question_editor_from_games(self, question_id: int) -> None:
        self.set_section(2)
        self.questions_page.open_question(question_id)
        self.refresh_context_panels()

    def open_projector_window(self, full_screen: bool | None = None) -> None:
        if self._resolve_active_game() is None:
            self._show_warning("Сначала создайте и откройте игру.")
            return

        if full_screen is None:
            full_screen = self.services.settings_service.should_open_projector_fullscreen()

        if self.projector_window is None:
            self.projector_window = ProjectorWindow(self.services.presentation_service)
        elif self.projector_window.isMinimized():
            self.projector_window.showNormal()

        if full_screen:
            if not self.projector_window.isFullScreen():
                self.projector_window.showFullScreen()
        else:
            # Preserve the user-selected projector size in normal window mode.
            if self.projector_window.isFullScreen():
                self.projector_window.showNormal()
            elif not self.projector_window.isVisible():
                self.projector_window.show()

        if not self.projector_window.isVisible():
            self.projector_window.show()
        self.projector_window.raise_()
        self.raise_()
        self.activateWindow()

    def show_welcome_screen(self, open_window: bool = False) -> None:
        game = self._resolve_active_game()
        if game is None:
            self.services.presentation_service.show_welcome(
                subtitle=self.services.settings_service.get_welcome_subtitle()
            )
        else:
            self.services.presentation_service.show_welcome(
                title=game.title,
                subtitle=self.services.settings_service.get_welcome_subtitle(),
                logo=self._get_game_logo(game.id),
                background=self._get_game_splash_media(game.id),
            )
        self._update_session_live_state(display_phase="welcome", round_id=None, question_id=None)

        if open_window:
            self.open_projector_window()

    def show_waiting_screen(self) -> None:
        game = self._resolve_active_game()
        if game is None:
            self._show_warning("Сначала выберите игру.")
            return

        waiting_background = self._get_waiting_background_media(game.id)
        if waiting_background is None:
            waiting_background = self._get_game_splash_media(game.id)

        self.services.presentation_service.show_waiting(
            game=game,
            logo=self._get_game_logo(game.id),
            background=waiting_background,
        )
        self._update_session_live_state(
            display_phase="waiting",
            round_id=self._resolve_active_round().id if self._resolve_active_round() is not None else None,
            question_id=self._resolve_active_question().id if self._resolve_active_question() is not None else None,
        )
        self.open_projector_window()

    def show_selected_game(self) -> None:
        game = self._resolve_active_game()
        if game is None:
            self._show_warning("Сначала выберите игру.")
            return
        self.services.presentation_service.show_game(
            game=game,
            logo=self._get_game_logo(game.id),
            background=self._get_game_splash_media(game.id),
        )
        self.open_projector_window()

    def show_partner_block(self) -> None:
        game = self._resolve_active_game()
        if game is None:
            self._show_warning("Сначала выберите игру.")
            return

        self.services.presentation_service.show_partner_block(
            game=game,
            partner_media=self._get_partner_media(game.id),
            logo=self._get_game_logo(game.id),
        )
        self._update_session_live_state(display_phase="sponsor", round_id=None, question_id=None)
        self.open_projector_window()

    def show_selected_round(self) -> None:
        round_item = self._resolve_active_round()
        if round_item is None:
            self._show_warning("Сначала выберите раунд.")
            return

        game = self.services.game_service.get_game(round_item.game_id)
        game_title = game.title if game else "Без игры"
        game_id = game.id if game is not None else round_item.game_id
        self.services.timer_service.clear()
        self.services.presentation_service.show_round(
            round_item=round_item,
            game_title=game_title,
            logo=self._get_game_logo(game_id),
            round_media=self._get_round_media(game_id, round_item.id),
            footer_text=(
                f"{self._round_type_label(round_item.round_type)}"
                + (
                    f" · Таймер по умолчанию: {round_item.timer_seconds} сек"
                    if round_item.timer_seconds > 0
                    else " · Без таймера"
                )
            ),
        )
        self._update_session_live_state(display_phase="round", round_id=round_item.id, question_id=None)
        self.open_projector_window()

    def show_round_answers_screen(self) -> None:
        round_item = self._resolve_active_round()
        if round_item is None:
            self._show_warning("Сначала выберите раунд.")
            return

        game = self.services.game_service.get_game(round_item.game_id)
        game_title = game.title if game else "Без игры"
        game_id = game.id if game is not None else round_item.game_id
        self.services.timer_service.clear()
        self.services.presentation_service.show_round(
            round_item=round_item,
            game_title=game_title,
            logo=self._get_game_logo(game_id),
            round_media=self._get_round_media(game_id, round_item.id),
            subtitle_text=f"{self._round_type_label(round_item.round_type)}",
            body_text="Сейчас узнаем правильные ответы.",
            footer_text="Открывайте ответы по одному",
        )
        self._update_session_live_state(display_phase="round_answers", round_id=round_item.id, question_id=None)
        self.open_projector_window()

    def show_selected_question(self) -> None:
        question = self._resolve_active_question()
        if question is None:
            self._show_warning("Сначала выберите вопрос.")
            return

        self._present_question(question)

    def _present_question(
        self,
        question,
        *,
        emphasize_media: bool = False,
        preserve_timer: bool = False,
    ) -> None:
        round_item = self.services.round_service.get_round(question.round_id)
        round_title = round_item.title if round_item else "Без раунда"
        round_questions = self.services.question_service.list_questions_by_round(question.round_id)
        game = self._resolve_active_game()
        if game is None and round_item is not None:
            game = self.services.game_service.get_game(round_item.game_id)
        game_id = game.id if game is not None else (round_item.game_id if round_item is not None else 0)
        if not preserve_timer:
            self._prepare_question_timer(question)
        self.services.presentation_service.show_question(
            question=question,
            round_title=round_title,
            options=self._build_question_options(question),
            option_media_paths=self._build_option_media_paths(game_id, question.id) if game_id else [],
            logo=None,
            question_media=self._get_primary_question_stage_media(game_id, question.id, "question") if game_id else None,
            footer_text="",
            top_left_text=self._build_question_counter_text(question, round_questions),
            top_right_text=f"Очки: {question.points}",
            emphasize_media=emphasize_media,
        )
        self._update_session_live_state(
            display_phase="question",
            round_id=round_item.id if round_item is not None else None,
            question_id=question.id,
        )
        self.open_projector_window()

    def hide_question_screen(self) -> None:
        round_item = self._resolve_active_round()

        if round_item is None:
            question = self._resolve_active_question()
            if question is not None:
                round_item = self.services.round_service.get_round(question.round_id)

        if round_item is not None:
            if round_item.id in self.completed_round_ids:
                self.show_round_answers_screen()
                return
            self.show_round_by_id(round_item.id)
            return

        self.show_waiting_screen()

    def show_answer_screen(self) -> None:
        question = self._resolve_active_question()
        if question is None:
            self._show_warning("Сначала выберите вопрос.")
            return

        self._present_answer(question)

    def _present_answer(
        self,
        question,
        *,
        emphasize_media: bool = False,
    ) -> None:
        round_item = self.services.round_service.get_round(question.round_id)
        round_title = round_item.title if round_item else "Без раунда"
        round_questions = self.services.question_service.list_questions_by_round(question.round_id)
        game = self._resolve_active_game()
        if game is None and round_item is not None:
            game = self.services.game_service.get_game(round_item.game_id)
        game_id = game.id if game is not None else (round_item.game_id if round_item is not None else 0)
        answer_media = self._get_primary_question_stage_media(game_id, question.id, "answer") if game_id else None
        if answer_media is None and game_id:
            answer_media = self._get_primary_question_stage_media(game_id, question.id, "question")

        self.services.presentation_service.show_answer(
            question=question,
            round_title=round_title,
            resolved_answer=self._resolve_answer_text(question),
            options=self._build_question_options(question),
            option_media_paths=self._build_option_media_paths(game_id, question.id) if game_id else [],
            highlighted_option_index=self._resolve_answer_option_index(question),
            logo=None,
            answer_media=answer_media,
            top_left_text=self._build_question_counter_text(question, round_questions),
            top_right_text=f"Очки: {question.points}",
            emphasize_media=emphasize_media,
        )
        self._update_session_live_state(
            display_phase="answer",
            round_id=round_item.id if round_item is not None else None,
            question_id=question.id,
        )
        self.open_projector_window()

    def play_background_music(self) -> None:
        game = self._resolve_active_game()
        if game is None:
            self._show_warning("Сначала выберите игру для фоновой музыки.")
            return

        background_music = self._get_background_music_media(game.id)
        if background_music is None:
            self._show_warning("Для выбранной игры не назначена фоновая музыка.")
            return

        self.open_projector_window()
        if self.projector_window is not None:
            self.projector_window.play_background_music(background_music.file_path)
        self.services.presentation_service.set_music_status("Фоновая музыка включена")

    def stop_background_music(self) -> None:
        if self.projector_window is not None:
            self.projector_window.stop_background_music()
        self.services.presentation_service.set_music_status("")

    def start_timer(self) -> None:
        if self.services.timer_service.state.total_seconds <= 0:
            question = self._resolve_active_question()
            if question is not None:
                self._prepare_question_timer(question)
            else:
                self._show_warning("Сначала выберите вопрос с таймером.")
                return
        if self.services.timer_service.state.total_seconds <= 0:
            self._show_warning("У выбранного вопроса таймер не задан.")
            return
        self.services.timer_service.start()

    def pause_timer(self) -> None:
        self.services.timer_service.pause()

    def resume_timer(self) -> None:
        self.services.timer_service.resume()

    def reset_timer(self) -> None:
        timer_state = self.services.timer_service.state
        if timer_state.total_seconds <= 0:
            question = self._resolve_active_question()
            if question is not None:
                self._prepare_question_timer(question)
                return
            self._show_warning("Сначала выберите вопрос с таймером.")
            return
        self.services.timer_service.reset()

    def show_next_question(self) -> None:
        question = self.games_page.select_next_question()
        if question is None:
            self._show_warning("Следующего вопроса больше нет.")
            return
        self.show_selected_question()

    def show_previous_question(self) -> None:
        question = self.games_page.select_previous_question()
        if question is None:
            self._show_warning("Предыдущего вопроса больше нет.")
            return
        self.show_selected_question()

    def show_scoreboard(self) -> None:
        game = self._resolve_active_game()
        if game is None:
            self._show_warning("Сначала выберите игру для таблицы очков.")
            return

        scoreboard_rows = self._get_live_scoreboard_rows(game.id)
        rounds = self.services.round_service.list_rounds_by_game(game.id)
        self.services.presentation_service.show_scores(
            game_title=game.title,
            scoreboard_rows=scoreboard_rows,
            round_titles=[round_item.title for round_item in rounds],
            logo=self._get_game_logo(game.id),
        )
        self._update_session_live_state(
            display_phase="scores",
            round_id=self._resolve_active_round().id if self._resolve_active_round() is not None else None,
            question_id=None,
        )
        self.open_projector_window()

    def show_score_column(self) -> None:
        game = self._resolve_active_game()
        if game is None:
            self._show_warning("Сначала выберите игру для показа очков.")
            return

        scoreboard_rows = self._get_live_scoreboard_rows(game.id)
        self.services.presentation_service.show_scores(
            game_title=game.title,
            scoreboard_rows=scoreboard_rows,
            round_titles=[],
            logo=self._get_game_logo(game.id),
            totals_only=True,
            title="Колонка очков",
            footer="Показан только общий итог команд",
        )
        self._update_session_live_state(
            display_phase="score_column",
            round_id=self._resolve_active_round().id if self._resolve_active_round() is not None else None,
            question_id=None,
        )
        self.open_projector_window()

    def show_teams_screen(self) -> None:
        game = self._resolve_active_game()
        if game is None:
            self._show_warning("Сначала выберите игру для показа команд.")
            return

        teams = self._get_live_teams(game.id)
        if not teams:
            self._show_warning("Для выбранной игры пока нет команд.")
            return

        self.services.presentation_service.show_teams(
            game_title=game.title,
            teams=teams,
            logo=self._get_game_logo(game.id),
        )
        self._update_session_live_state(display_phase="teams", round_id=None, question_id=None)
        self.open_projector_window()

    def show_winners_screen(self) -> None:
        game = self._resolve_active_game()
        if game is None:
            self._show_warning("Сначала выберите игру для показа победителей.")
            return

        winners = self._get_live_winners(game.id)
        if not winners:
            self._show_warning("Для выбранной игры пока нет команд.")
            return

        self.services.presentation_service.show_winners(
            game_title=game.title,
            winners=winners,
            logo=self._get_game_logo(game.id),
        )
        self._update_session_live_state(display_phase="winners", round_id=None, question_id=None)
        self.open_projector_window()

    def show_game_media_asset(self, media_id: int) -> None:
        game = self._resolve_active_game()
        if game is None:
            self._show_warning("Сначала выберите игру.")
            return

        media = self.services.media_service.get_media(media_id)
        if media is None:
            self._show_warning("Файл игры не найден.")
            return

        self.services.presentation_service.show_media_asset(
            game_title=game.title,
            media=media,
            logo=self._get_game_logo(game.id),
        )
        self._update_session_live_state(
            display_phase="media",
            round_id=media.round_id,
            question_id=media.question_id,
        )
        self.open_projector_window()

    def show_connection_code_screen(self) -> None:
        game = self._resolve_active_game()
        if game is None:
            self._show_warning("Сначала выберите игру.")
            return

        self.services.presentation_service.show_connection_code(
            game_title=game.title,
            connection_code=self._build_connection_code(game.id),
            logo=self._get_game_logo(game.id),
        )
        self._update_session_live_state(display_phase="qr", round_id=None, question_id=None)
        self.open_projector_window()

    def show_round_by_id(self, round_id: int) -> None:
        if round_id <= 0:
            return
        if hasattr(self.games_page, "_select_round"):
            self.games_page._select_round(round_id)
        self.refresh_context_panels()
        self.show_selected_round()

    def select_round_in_control_panel(self, round_id: int) -> None:
        if round_id <= 0:
            return
        if hasattr(self.games_page, "_select_round"):
            self.games_page._select_round(round_id)
        self.refresh_context_panels()

    def show_question_by_id(self, question_id: int) -> None:
        if question_id <= 0:
            return
        question = self.services.question_service.get_question(question_id)
        if question is None:
            self._show_warning("Вопрос не найден.")
            return
        if hasattr(self.games_page, "_select_question"):
            self.games_page._select_question(question_id)
        self.refresh_context_panels()
        self._present_question(question)

    def show_answer_by_id(self, question_id: int) -> None:
        if question_id <= 0:
            return
        question = self.services.question_service.get_question(question_id)
        if question is None:
            self._show_warning("Вопрос не найден.")
            return
        if hasattr(self.games_page, "_select_question"):
            self.games_page._select_question(question_id)
        self.refresh_context_panels()
        self._present_answer(question)

    def start_timer_for_question(self, question_id: int) -> None:
        if question_id <= 0:
            return
        if hasattr(self.games_page, "_select_question"):
            self.games_page._select_question(question_id)
        self.refresh_context_panels()
        question = self._resolve_active_question()
        if question is None:
            self._show_warning("Сначала выберите вопрос.")
            return
        self._prepare_question_timer(question)
        self.services.timer_service.start()

    def pause_timer_for_question(self, question_id: int) -> None:
        if question_id <= 0:
            return
        if hasattr(self.games_page, "_select_question"):
            self.games_page._select_question(question_id)
        self.refresh_context_panels()
        self.services.timer_service.pause()

    def reset_timer_for_question(self, question_id: int) -> None:
        if question_id <= 0:
            return
        if hasattr(self.games_page, "_select_question"):
            self.games_page._select_question(question_id)
        self.refresh_context_panels()
        question = self._resolve_active_question()
        if question is None:
            self._show_warning("Сначала выберите вопрос.")
            return
        self._prepare_question_timer(question)

    def stop_answers_for_question(self, question_id: int) -> None:
        if question_id > 0 and hasattr(self.games_page, "_select_question"):
            self.games_page._select_question(question_id)
            self.refresh_context_panels()
        self.services.timer_service.pause()

    def show_question_media_by_id(self, question_id: int) -> None:
        if question_id <= 0:
            return
        if hasattr(self.games_page, "_select_question"):
            self.games_page._select_question(question_id)
        self.refresh_context_panels()

        question = self._resolve_active_question()
        game = self._resolve_active_game()
        if question is None or game is None:
            self._show_warning("Сначала выберите вопрос и игру.")
            return

        media = self._get_primary_question_stage_media(game.id, question.id, "question")
        if media is None:
            self._show_warning("У этого вопроса нет отдельного медиа вопроса.")
            return

        preserve_timer = False
        toggle_off = False
        if self.running_session_id is not None:
            session = self.services.game_session_service.get_session(self.running_session_id)
            preserve_timer = (
                session is not None
                and session.display_phase == "question"
                and session.active_question_id == question.id
            )
            toggle_off = (
                preserve_timer
                and self.services.presentation_service.state.scene == "question"
                and self.services.presentation_service.state.emphasize_media
            )

        self._present_question(
            question,
            emphasize_media=not toggle_off,
            preserve_timer=preserve_timer,
        )

    def show_answer_media_by_id(self, question_id: int) -> None:
        if question_id <= 0:
            return
        if hasattr(self.games_page, "_select_question"):
            self.games_page._select_question(question_id)
        self.refresh_context_panels()

        question = self._resolve_active_question()
        game = self._resolve_active_game()
        if question is None or game is None:
            self._show_warning("Сначала выберите вопрос и игру.")
            return

        media = self._get_primary_question_stage_media(game.id, question.id, "answer")
        if media is None:
            self._show_warning("У этого вопроса нет отдельного медиа ответа.")
            return

        toggle_off = False
        if self.running_session_id is not None:
            session = self.services.game_session_service.get_session(self.running_session_id)
            toggle_off = (
                session is not None
                and session.display_phase == "answer"
                and session.active_question_id == question.id
                and self.services.presentation_service.state.scene == "answer"
                and self.services.presentation_service.state.emphasize_media
            )

        self._present_answer(question, emphasize_media=not toggle_off)

    def finish_current_round(self) -> None:
        round_item = self._resolve_active_round()
        if round_item is None:
            self._show_warning("Сначала выберите раунд.")
            return

        self.completed_round_ids.add(round_item.id)
        if self.running_session_id is not None:
            self.services.game_session_service.mark_round_completed(
                self.running_session_id,
                round_item.id,
            )
        self.services.timer_service.pause()
        self._update_session_live_state(
            display_phase="round_answers",
            round_id=round_item.id,
            question_id=None,
        )
        self.refresh_context_panels()
        self.show_round_answers_screen()

    def _resolve_active_game(self) -> Game | None:
        if self.page_stack.currentWidget() is self.game_control_page:
            live_game = self._get_running_game()
            if live_game is not None:
                return live_game
        current_page = self.page_stack.currentWidget()
        if current_page is self.games_page:
            return self.games_page.get_selected_game()
        if current_page is self.rounds_page:
            return self.rounds_page.get_selected_game()
        if current_page is self.questions_page:
            return self.questions_page.get_selected_game()
        if current_page is self.media_page:
            return self.media_page.get_selected_game()
        if current_page is self.teams_page:
            return self.teams_page.get_selected_game()
        if current_page is self.scores_page:
            return self.scores_page.get_selected_game()
        return self.games_page.get_selected_game()

    def _get_running_game(self) -> Game | None:
        if self.running_game_id is None:
            return None
        return self.services.game_service.get_game(self.running_game_id)

    def _apply_live_session_context(self, game_id: int, session_id: int) -> None:
        self.rounds_page.set_current_game(game_id)
        self.questions_page.set_current_game(game_id)
        self.media_page.set_current_game(game_id)
        self.teams_page.set_current_session(session_id, game_id)
        self.scores_page.set_current_session(session_id, game_id)

    def _restore_live_session_state(self, session) -> None:
        rounds = self.services.round_service.list_rounds_by_game(session.game_id)
        if (
            session.active_round_id is not None
            and hasattr(self.games_page, "_select_round")
        ):
            self.games_page._select_round(session.active_round_id)
        elif rounds and self.games_page.get_selected_round() is None and hasattr(self.games_page, "_select_round"):
            self.games_page._select_round(rounds[0].id)

        if (
            session.active_question_id is not None
            and hasattr(self.games_page, "_select_question")
        ):
            self.games_page._select_question(session.active_question_id)

    def _resume_session_presentation(self, session) -> None:
        handlers = {
            "welcome": self.show_welcome_screen,
            "waiting": self.show_waiting_screen,
            "round": self.show_selected_round,
            "round_answers": self.show_round_answers_screen,
            "question": self.show_selected_question,
            "answer": self.show_answer_screen,
            "scores": self.show_scoreboard,
            "score_column": self.show_score_column,
            "teams": self.show_teams_screen,
            "winners": self.show_winners_screen,
            "qr": self.show_connection_code_screen,
            "sponsor": self.show_partner_block,
        }
        handler = handlers.get(session.display_phase)
        if handler is None:
            return
        handler()

    def _get_live_teams(self, game_id: int):
        if self.running_session_id is not None:
            return self.services.team_service.list_teams_by_session(self.running_session_id)
        return self.services.team_service.list_teams_by_game(game_id)

    def _get_live_scoreboard_rows(self, game_id: int):
        if self.running_session_id is not None:
            return self.services.score_service.get_scoreboard_rows_for_session(
                self.running_session_id,
                game_id,
            )
        return self.services.score_service.get_scoreboard_rows(game_id)

    def _get_live_winners(self, game_id: int):
        if self.running_session_id is not None:
            return self.services.score_service.get_winner_places_for_session(
                self.running_session_id
            )
        return self.services.score_service.get_winner_places(game_id)

    def _resolve_active_round(self):
        current_page = self.page_stack.currentWidget()
        if current_page is self.games_page:
            return self.games_page.get_selected_round()
        if current_page is self.rounds_page:
            return self.rounds_page.get_selected_round()
        if current_page is self.questions_page:
            return self.questions_page.get_selected_round()
        return self.games_page.get_selected_round()

    def _resolve_active_question(self):
        current_page = self.page_stack.currentWidget()
        if current_page is self.games_page:
            return self.games_page.get_selected_question()
        if current_page is self.questions_page:
            return self.questions_page.get_selected_question()
        return self.games_page.get_selected_question()

    def _get_game_logo(self, game_id: int):
        return self.services.media_service.find_media_for_game(game_id, "game_logo")

    def _get_game_splash_media(self, game_id: int):
        return self.services.media_service.find_media_for_game(game_id, "game_splash")

    def _get_waiting_background_media(self, game_id: int):
        return self.services.media_service.find_media_for_game(game_id, "waiting_background")

    def _get_partner_media(self, game_id: int):
        return self.services.media_service.find_media_for_game(game_id, "sponsor")

    def _get_background_music_media(self, game_id: int):
        return self.services.media_service.find_media_for_game(game_id, "background_music")

    def _get_round_media(self, game_id: int, round_id: int):
        return self.services.media_service.find_media_for_round(
            game_id=game_id,
            round_id=round_id,
            usage_role="round",
        )

    def _get_question_media(self, game_id: int, question_id: int):
        return self.services.media_service.find_media_for_question(
            game_id=game_id,
            question_id=question_id,
            usage_role="question",
        )

    def _get_answer_media(self, game_id: int, question_id: int):
        return self.services.media_service.find_media_for_question(
            game_id=game_id,
            question_id=question_id,
            usage_role="answer",
        )

    def _get_primary_question_stage_media(self, game_id: int, question_id: int, stage: str):
        role_priority = {
            "question": ["question_image", "question_video", "question_audio", "question"],
            "answer": ["answer_image", "answer_video", "answer_audio", "answer"],
        }.get(stage, [])
        for usage_role in role_priority:
            media = self.services.media_service.find_media_for_question(
                game_id=game_id,
                question_id=question_id,
                usage_role=usage_role,
            )
            if media is not None:
                return media
        return None

    def _build_option_media_paths(self, game_id: int, question_id: int) -> list[str | None]:
        result: list[str | None] = []
        for usage_role in (
            "option_a_image",
            "option_b_image",
            "option_c_image",
            "option_d_image",
        ):
            media = self.services.media_service.find_media_for_question(
                game_id=game_id,
                question_id=question_id,
                usage_role=usage_role,
            )
            result.append(media.file_path if media is not None else None)
        return result

    def _build_question_options(self, question) -> list[str]:
        if question.question_type != "abcd":
            return []
        return [
            f"A. {question.option_a}",
            f"B. {question.option_b}",
            f"C. {question.option_c}",
            f"D. {question.option_d}",
        ]

    def _resolve_answer_text(self, question) -> str:
        if question.question_type != "abcd":
            return question.answer

        options_map = {
            "A": question.option_a,
            "B": question.option_b,
            "C": question.option_c,
            "D": question.option_d,
        }
        option_text = options_map.get(question.answer.upper(), "")
        if option_text:
            return f"{question.answer.upper()}. {option_text}"
        return question.answer

    def _resolve_answer_option_index(self, question) -> int:
        if question.question_type != "abcd":
            return -1
        return {
            "A": 0,
            "B": 1,
            "C": 2,
            "D": 3,
        }.get(question.answer.upper(), -1)

    def _prepare_question_timer(self, question) -> None:
        timer_seconds, source_label = self._resolve_question_timer(question)
        if timer_seconds > 0:
            self.services.timer_service.configure(
                total_seconds=timer_seconds,
                source_label=source_label,
            )
        else:
            self.services.timer_service.clear()

    @staticmethod
    def _build_question_counter_text(question, round_questions) -> str:
        total_questions = len(round_questions or [])
        if total_questions > 0:
            return f"Вопрос {question.order_index}/{total_questions}"
        return f"Вопрос {question.order_index}"

    def _resolve_question_timer(self, question) -> tuple[int, str]:
        if question.timer_seconds > 0:
            return question.timer_seconds, "Таймер вопроса"
        round_item = self.services.round_service.get_round(question.round_id)
        if round_item is not None and round_item.timer_seconds > 0:
            return round_item.timer_seconds, f"Таймер раунда «{round_item.title}»"
        return 0, "Без таймера"

    def _update_session_live_state(
        self,
        display_phase: str,
        round_id: int | None,
        question_id: int | None,
    ) -> None:
        if self.running_session_id is None:
            return
        self.services.game_session_service.update_live_state(
            session_id=self.running_session_id,
            active_round_id=round_id,
            active_question_id=question_id,
            display_phase=display_phase,
        )

    @staticmethod
    def _round_type_label(round_type: str) -> str:
        return {
            "standard": "Стандартный раунд",
            "media": "Медиа-раунд",
            "blitz": "Блиц",
            "final": "Финал",
        }.get(round_type, round_type)

    @staticmethod
    def _build_connection_code(game_id: int) -> str:
        return f"QM-{game_id:04d}"

    def _show_warning(self, message: str) -> None:
        QMessageBox.warning(self, "Quiz Meetup", message)

    def _build_hotkeys(self) -> None:
        shortcuts = [
            ("Space", self._toggle_question_visibility),
            ("T", self._toggle_timer_from_hotkey),
            ("A", self.show_answer_screen),
            ("S", self.show_scoreboard),
            ("N", self.show_next_question),
            ("P", self.show_previous_question),
        ]
        for key_sequence, handler in shortcuts:
            shortcut = QShortcut(QKeySequence(key_sequence), self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(handler)
            self.hotkey_shortcuts.append(shortcut)

        fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        fullscreen_shortcut.setContext(Qt.ApplicationShortcut)
        fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self.hotkey_shortcuts.append(fullscreen_shortcut)
        self._update_hotkey_states()

    def _update_hotkey_states(self) -> None:
        enabled = self.page_stack.currentWidget() is self.game_control_page
        for shortcut in self.hotkey_shortcuts:
            if shortcut.key().toString() == "F11":
                shortcut.setEnabled(True)
            else:
                shortcut.setEnabled(enabled)

    def _toggle_question_visibility(self) -> None:
        if self.services.presentation_service.state.scene == "question":
            self.hide_question_screen()
        else:
            self.show_selected_question()

    def _toggle_timer_from_hotkey(self) -> None:
        timer_status = self.services.timer_service.state.status
        if timer_status == "running":
            self.pause_timer()
        elif timer_status == "paused":
            self.resume_timer()
        else:
            self.start_timer()

    def _set_autosave_status(self, message: str) -> None:
        self.autosave_badge.setText(message)

    def _update_header_context(self) -> None:
        current_index = self.page_stack.currentIndex()
        title, description, _page = self.section_definitions[current_index]
        quick_new_visible = False
        quick_projector_visible = False
        quick_projector_enabled = False

        if self.page_stack.currentWidget() is self.games_page:
            title, description = self.games_page.header_context()
            quick_new_visible = False
            quick_projector_visible = self.games_page.is_editor_visible()
            quick_projector_enabled = self.games_page.get_selected_game() is not None
        elif self.page_stack.currentWidget() is self.game_control_page:
            live_game = self._get_running_game()
            title = "Панель ведущего"
            quick_projector_visible = True
            quick_projector_enabled = live_game is not None
            if live_game is not None:
                description = (
                    f"Сейчас запущена игра «{live_game.title}». "
                    "Здесь ведущий управляет проектором, общими файлами, раундами, вопросами и ручными очками."
                )
            else:
                description = (
                    "Сначала запустите готовую игру из списка в разделе «Игры», "
                    "потом управляйте ею отсюда."
                )

        self.section_title_label.setText(title)
        self.section_description_label.setText(description)
        self.quick_new_game_button.setVisible(quick_new_visible)
        self.quick_projector_button.setVisible(quick_projector_visible)
        self.quick_projector_button.setEnabled(quick_projector_enabled)
        self.quick_fullscreen_button.setVisible(True)

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.setWindowState((self.windowState() & ~Qt.WindowFullScreen) | Qt.WindowMaximized)
            self.show()
        else:
            self.setWindowState(self.windowState() | Qt.WindowFullScreen)
            self.show()

    def toggle_maximized(self) -> None:
        if self.isFullScreen():
            self.setWindowState((self.windowState() & ~Qt.WindowFullScreen) | Qt.WindowMaximized)
            self.show()
            return

        if self.isMaximized():
            self.setWindowState(self.windowState() & ~Qt.WindowMaximized)
            self.showNormal()
        else:
            self.setWindowState(self.windowState() | Qt.WindowMaximized)
            self.show()

    def changeEvent(self, event) -> None:  # type: ignore[override]
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isFullScreen():
                self.quick_fullscreen_button.setText("Обычный размер")
            elif self.isMaximized():
                self.quick_fullscreen_button.setText("Обычный размер")
            else:
                self.quick_fullscreen_button.setText("Развернуть окно")
        super().changeEvent(event)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.games_page.flush_autosave()
        self.stop_background_music()
        super().closeEvent(event)

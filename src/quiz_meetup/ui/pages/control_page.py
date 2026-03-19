from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from quiz_meetup.models import Game, MediaAsset, Question, Round
from quiz_meetup.ui.icons import apply_button_icon


class GameControlPage(QWidget):
    open_projector_requested = Signal()
    show_splash_requested = Signal()
    show_waiting_requested = Signal()
    show_qr_requested = Signal()
    show_score_column_requested = Signal()
    hide_score_column_requested = Signal()
    hide_scores_requested = Signal()
    start_timer_requested = Signal()
    pause_timer_requested = Signal()
    resume_timer_requested = Signal()
    reset_timer_requested = Signal()
    play_sponsor_requested = Signal()
    play_background_music_requested = Signal()
    stop_background_music_requested = Signal()
    show_round_requested = Signal()
    show_question_requested = Signal()
    hide_question_requested = Signal()
    show_answer_requested = Signal()
    show_scores_requested = Signal()
    show_teams_requested = Signal()
    show_winners_requested = Signal()
    next_question_requested = Signal()
    previous_question_requested = Signal()
    show_media_requested = Signal(int)
    select_round_by_id_requested = Signal(int)
    show_round_by_id_requested = Signal(int)
    show_question_by_id_requested = Signal(int)
    show_answer_by_id_requested = Signal(int)
    start_timer_for_question_requested = Signal(int)
    stop_answers_for_question_requested = Signal(int)
    pause_timer_for_question_requested = Signal(int)
    reset_timer_for_question_requested = Signal(int)
    show_question_media_by_id_requested = Signal(int)
    show_answer_media_by_id_requested = Signal(int)
    finish_round_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.screen_toggle_buttons: dict[str, QPushButton] = {}
        self.start_action_buttons: list[QPushButton] = []
        self.screen_control_order: list[tuple[str, QPushButton]] = []
        self.score_action_buttons: list[QPushButton] = []
        self.expanded_question_id: int | None = None
        self._dashboard_questions: list[Question] = []
        self._dashboard_current_question_id: int | None = None
        self._dashboard_round_completed = False
        self._dashboard_media_assets: list[MediaAsset] = []
        self._dashboard_rounds: list[Round] = []
        self._dashboard_selected_round_id: int | None = None
        self._dashboard_game_level_media: list[MediaAsset] = []
        self._game_started = False
        self._current_dashboard_game_id: int | None = None

        self.current_game_label = QLabel("Игра не выбрана")
        self.current_game_label.setObjectName("DetailsLabel")
        self.current_round_label = QLabel("Раунд не выбран")
        self.current_round_label.setObjectName("DetailsLabel")
        self.current_question_label = QLabel("Вопрос не выбран")
        self.current_question_label.setObjectName("DetailsLabel")
        self.projector_state_label = QLabel("Проектор ждёт команду ведущего.")
        self.projector_state_label.setObjectName("DetailsLabel")
        self.music_state_label = QLabel("Фоновая музыка выключена")
        self.music_state_label.setObjectName("DetailsLabel")
        self.timer_value_label = QLabel("--:--")
        self.timer_value_label.setObjectName("ControlTimerValue")
        self.timer_value_label.setAlignment(Qt.AlignCenter)
        self.timer_source_label = QLabel("Таймер не подготовлен")
        self.timer_source_label.setObjectName("DetailsLabel")
        self.timer_status_label = QLabel("Статус таймера: не запущен")
        self.timer_status_label.setObjectName("DetailsLabel")

        self.start_info_label = QLabel(
            "Это отдельный режим проведения игры. Здесь ведущий запускает экраны, вопросы, таймер и результаты."
        )
        self.start_info_label.setWordWrap(True)
        self.start_info_label.setObjectName("PageHint")

        self.media_state_label = QLabel("Для этой игры пока нет общих файлов.")
        self.media_state_label.setWordWrap(True)
        self.media_state_label.setObjectName("DetailsLabel")

        self.round_state_label = QLabel("Для этой игры пока нет раундов.")
        self.round_state_label.setWordWrap(True)
        self.round_state_label.setObjectName("DetailsLabel")

        self.round_summary_label = QLabel("Выберите раунд, чтобы увидеть его вопросы.")
        self.round_summary_label.setWordWrap(True)
        self.round_summary_label.setObjectName("DetailsLabel")
        self.round_completion_label = QLabel("Раунд ещё не завершён. Сначала показывайте вопросы, потом завершайте раунд.")
        self.round_completion_label.setWordWrap(True)
        self.round_completion_label.setObjectName("DetailsLabel")

        self.questions_state_label = QLabel("В выбранном раунде пока нет вопросов.")
        self.questions_state_label.setWordWrap(True)
        self.questions_state_label.setObjectName("DetailsLabel")

        self.score_hint_label = QLabel(
            "Баллы по раундам редактируются вручную. Итог и места команд пересчитываются автоматически."
        )
        self.score_hint_label.setWordWrap(True)
        self.score_hint_label.setObjectName("DetailsLabel")

        self.hotkeys_label = QLabel(
            "Горячие клавиши:\n"
            "Space — показать/скрыть вопрос\n"
            "T — старт/пауза таймера\n"
            "A — показать ответ\n"
            "S — показать таблицу\n"
            "N — следующий вопрос\n"
            "P — предыдущий вопрос"
        )
        self.hotkeys_label.setWordWrap(True)
        self.hotkeys_label.setObjectName("DetailsLabel")

        self.media_buttons_widget = QWidget()
        self.media_buttons_layout = QGridLayout(self.media_buttons_widget)
        self.media_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.media_buttons_layout.setHorizontalSpacing(12)
        self.media_buttons_layout.setVerticalSpacing(12)

        self.round_buttons_widget = QWidget()
        self.round_buttons_layout = QGridLayout(self.round_buttons_widget)
        self.round_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.round_buttons_layout.setHorizontalSpacing(12)
        self.round_buttons_layout.setVerticalSpacing(12)

        self.questions_cards_widget = QWidget()
        self.questions_cards_layout = QVBoxLayout(self.questions_cards_widget)
        self.questions_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.questions_cards_layout.setSpacing(12)

        self.start_actions_widget = QWidget()
        self.start_actions_layout = QGridLayout(self.start_actions_widget)
        self.start_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.start_actions_layout.setHorizontalSpacing(12)
        self.start_actions_layout.setVerticalSpacing(12)

        self.screen_controls_widget = QWidget()
        self.screen_controls_layout = QGridLayout(self.screen_controls_widget)
        self.screen_controls_layout.setContentsMargins(0, 0, 0, 0)
        self.screen_controls_layout.setHorizontalSpacing(12)
        self.screen_controls_layout.setVerticalSpacing(12)

        self.score_actions_widget = QWidget()
        self.score_actions_layout = QGridLayout(self.score_actions_widget)
        self.score_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.score_actions_layout.setHorizontalSpacing(12)
        self.score_actions_layout.setVerticalSpacing(12)
        self.scroll_area: QScrollArea | None = None
        self.scroll_content: QWidget | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area = scroll_area

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.scroll_content = content
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        self.start_card = self._build_card(
            "1. Начало игры",
            [
                self.start_info_label,
                self.start_actions_widget,
            ],
        )
        content_layout.addWidget(self.start_card)

        self.screen_controls_card = self._build_card(
            "2. Управление экраном игры",
            [
                self.screen_controls_widget,
            ],
        )
        content_layout.addWidget(self.screen_controls_card)

        self.media_card = self._build_card(
            "3. Общие файлы игры",
            [
                self.media_state_label,
                self._build_button_row(
                    [
                        ("Остановить текущий файл", self.show_waiting_requested, "SecondaryButton", "Exit"),
                    ]
                ),
                self.media_buttons_widget,
            ],
        )
        content_layout.addWidget(self.media_card)

        self.rounds_questions_card = self._build_card(
            "4. Раунды и вопросы",
            [
                self.round_state_label,
                self.round_buttons_widget,
                self.round_summary_label,
                self.questions_state_label,
                self.questions_cards_widget,
                self._build_button_row(
                    [
                        ("Завершить раунд", self.finish_round_requested, "AccentButton", "Check_All_Big"),
                    ]
                ),
                self.round_completion_label,
            ],
        )
        content_layout.addWidget(self.rounds_questions_card)

        self.timer_navigation_card = self._build_card(
            "5. Таймер и навигация",
            [
                self._build_button_grid(
                    [
                        ("Предыдущий вопрос", self.previous_question_requested, "SecondaryButton", "Link"),
                        ("Следующий вопрос", self.next_question_requested, "AccentButton", "Check_Big"),
                        ("Скрыть вопрос", self.hide_question_requested, "SecondaryButton", "Filter"),
                        ("Показать раунд", self.show_round_requested, "SecondaryButton", "Book_Open"),
                    ],
                    columns=2,
                    min_height=52,
                ),
                self._build_timer_controls(),
            ],
        )
        content_layout.addWidget(self.timer_navigation_card)

        self.score_card = self._build_card(
            "6. Команды и счёт",
            [
                self.score_hint_label,
                self.score_actions_widget,
            ],
        )
        content_layout.addWidget(self.score_card)

        self.context_card = self._build_card(
            "7. Контекст ведущего",
            [
                self.current_game_label,
                self.current_round_label,
                self.current_question_label,
                self.projector_state_label,
                self.music_state_label,
                self.timer_value_label,
                self.timer_source_label,
                self.timer_status_label,
                self.hotkeys_label,
            ],
        )
        content_layout.addWidget(self.context_card)
        content_layout.addStretch(1)

        scroll_area.setWidget(content)
        root_layout.addWidget(scroll_area)
        self._build_static_buttons()
        self._apply_started_visibility()

    def _build_static_buttons(self) -> None:
        self.start_game_button = QPushButton("Начать игру")
        self.start_game_button.setMinimumHeight(52)
        self.start_game_button.setObjectName("AccentButton")
        self.start_game_button.clicked.connect(self._handle_game_start_requested)
        self._apply_button_icon_style(self.start_game_button, "AccentButton", "Star")

        self.open_projector_button = QPushButton("Открыть окно проектора")
        self.open_projector_button.setMinimumHeight(52)
        self.open_projector_button.setObjectName("SecondaryButton")
        self.open_projector_button.clicked.connect(
            lambda _checked=False: self.open_projector_requested.emit()
        )
        self._apply_button_icon_style(self.open_projector_button, "SecondaryButton", "External_Link")

        self.start_action_buttons = [
            self.start_game_button,
            self.open_projector_button,
        ]
        self._populate_grid(self.start_actions_layout, self.start_action_buttons, self._start_action_columns())

        self.screen_control_order = self._create_toggle_buttons(
            [
                ("splash", "Показать заставку", self.show_splash_requested, self.show_waiting_requested, "Star"),
                ("scores", "Показать таблицу", self.show_scores_requested, self.hide_scores_requested, "Chart_Bar_Vertical_01"),
                ("score_column", "Показать колонку очков", self.show_score_column_requested, self.hide_score_column_requested, "Chart_Bar_Vertical_01"),
                ("teams", "Представить команды", self.show_teams_requested, self.show_waiting_requested, "Main_Component"),
                ("winners", "Показать победителей", self.show_winners_requested, self.show_waiting_requested, "Check_All_Big"),
            ],
            min_height=52,
        )
        self._populate_grid(
            self.screen_controls_layout,
            [button for _, button in self.screen_control_order],
            self._screen_control_columns(),
        )

        self.score_action_buttons = self._create_action_buttons(
            [
                ("Открыть таблицу очков", self.show_scores_requested, "AccentButton", "Chart_Bar_Vertical_01"),
                ("Показать победителей", self.show_winners_requested, "SecondaryButton", "Check_All_Big"),
            ],
            min_height=52,
        )
        self._populate_grid(self.score_actions_layout, self.score_action_buttons, self._score_action_columns())

    def _build_card(self, title_text: str, widgets: list[QWidget]) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel(title_text)
        title.setObjectName("SectionCaption")
        layout.addWidget(title)
        for widget in widgets:
            layout.addWidget(widget)
        return card

    def _create_action_buttons(
        self,
        buttons: list[tuple[str, Signal, str, str | None]],
        min_height: int,
    ) -> list[QPushButton]:
        result: list[QPushButton] = []
        for title, signal, style_name, icon_name in buttons:
            button = QPushButton(title)
            button.setMinimumHeight(min_height)
            button.setObjectName(style_name)
            button.clicked.connect(lambda _checked=False, current_signal=signal: current_signal.emit())
            self._apply_button_icon_style(button, style_name, icon_name)
            result.append(button)
        return result

    def _create_toggle_buttons(
        self,
        buttons: list[tuple[str, str, Signal, Signal, str | None]],
        min_height: int,
    ) -> list[tuple[str, QPushButton]]:
        result: list[tuple[str, QPushButton]] = []
        for key, title, on_signal, off_signal, icon_name in buttons:
            button = QPushButton(title)
            button.setMinimumHeight(min_height)
            button.setObjectName("SecondaryButton")
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked, current_on=on_signal, current_off=off_signal: (
                    current_on.emit() if checked else current_off.emit()
                )
            )
            if icon_name:
                button.toggled.connect(
                    lambda checked, current_button=button, current_icon=icon_name: self._update_toggle_icon(
                        current_button, current_icon, checked
                    )
                )
                self._update_toggle_icon(button, icon_name, False)
            self.screen_toggle_buttons[key] = button
            result.append((key, button))
        return result

    def _populate_grid(self, layout: QGridLayout, widgets: list[QWidget], columns: int) -> None:
        self._detach_layout_widgets(layout)
        safe_columns = max(1, columns)
        for index, widget in enumerate(widgets):
            layout.addWidget(widget, index // safe_columns, index % safe_columns)

    def _content_width(self) -> int:
        if self.scroll_area is not None:
            viewport_width = self.scroll_area.viewport().width()
            if viewport_width > 0:
                return viewport_width
        return max(0, self.width())

    def _start_action_columns(self) -> int:
        return 1 if self._content_width() < 1040 else 2

    def _screen_control_columns(self) -> int:
        width = self._content_width()
        if width < 980:
            return 1
        if width < 1320:
            return 2
        return 3

    def _media_button_columns(self) -> int:
        width = self._content_width()
        if width < 980:
            return 1
        if width < 1320:
            return 2
        return 4

    def _round_button_columns(self) -> int:
        width = self._content_width()
        if width < 980:
            return 1
        if width < 1320:
            return 2
        return 4

    def _score_action_columns(self) -> int:
        return 1 if self._content_width() < 1040 else 2

    def _question_action_columns(self) -> int:
        width = self._content_width()
        if width < 980:
            return 1
        return 2

    def _refresh_responsive_layouts(self) -> None:
        if self.start_action_buttons:
            self._populate_grid(self.start_actions_layout, self.start_action_buttons, self._start_action_columns())
        if self.screen_control_order:
            self._populate_grid(
                self.screen_controls_layout,
                [button for _, button in self.screen_control_order],
                self._screen_control_columns(),
            )
        if self.score_action_buttons:
            self._populate_grid(self.score_actions_layout, self.score_action_buttons, self._score_action_columns())
        if self._dashboard_game_level_media or self.media_buttons_layout.count():
            self._rebuild_media_buttons(self._dashboard_game_level_media)
        if self._dashboard_rounds or self.round_buttons_layout.count():
            self._rebuild_round_buttons(self._dashboard_rounds, self._dashboard_selected_round_id)
        if self._dashboard_questions or self.questions_cards_layout.count():
            self._rebuild_question_cards(
                self._dashboard_questions,
                self._dashboard_current_question_id,
                self._dashboard_round_completed,
                self._dashboard_media_assets,
            )

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._refresh_responsive_layouts()

    def _build_button_row(
        self,
        buttons: list[tuple[str, Signal, str, str | None]],
    ) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        for title, signal, style_name, icon_name in buttons:
            button = QPushButton(title)
            button.setMinimumHeight(52)
            button.setObjectName(style_name)
            button.clicked.connect(lambda _checked=False, current_signal=signal: current_signal.emit())
            self._apply_button_icon_style(button, style_name, icon_name)
            layout.addWidget(button)
        return widget

    def _build_button_grid(
        self,
        buttons: list[tuple[str, Signal, str, str | None]],
        columns: int,
        min_height: int,
    ) -> QWidget:
        widget = QWidget()
        grid = QGridLayout(widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        for index, (title, signal, style_name, icon_name) in enumerate(buttons):
            button = QPushButton(title)
            button.setMinimumHeight(min_height)
            button.setObjectName(style_name)
            button.clicked.connect(lambda _checked=False, current_signal=signal: current_signal.emit())
            self._apply_button_icon_style(button, style_name, icon_name)
            grid.addWidget(button, index // columns, index % columns)
        return widget

    def _build_toggle_grid(
        self,
        buttons: list[tuple[str, str, Signal, Signal, str | None]],
        columns: int,
        min_height: int,
    ) -> QWidget:
        widget = QWidget()
        grid = QGridLayout(widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        for index, (key, title, on_signal, off_signal, icon_name) in enumerate(buttons):
            button = QPushButton(title)
            button.setMinimumHeight(min_height)
            button.setObjectName("SecondaryButton")
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked, current_on=on_signal, current_off=off_signal: (
                    current_on.emit() if checked else current_off.emit()
                )
            )
            if icon_name:
                button.toggled.connect(
                    lambda checked, current_button=button, current_icon=icon_name: self._update_toggle_icon(
                        current_button, current_icon, checked
                    )
                )
                self._update_toggle_icon(button, icon_name, False)
            self.screen_toggle_buttons[key] = button
            grid.addWidget(button, index // columns, index % columns)
        return widget

    def _build_timer_controls(self) -> QWidget:
        widget = QWidget()
        grid = QGridLayout(widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        timer_buttons = [
            ("Запустить таймер", self.start_timer_requested, "AccentButton", "Check_Big"),
            ("Остановить приём ответов", self.pause_timer_requested, "SecondaryButton", "Filter"),
            ("Продолжить таймер", self.resume_timer_requested, "SecondaryButton", "Check_Big"),
            ("Сбросить таймер", self.reset_timer_requested, "SecondaryButton", "Trash_Empty"),
        ]
        for index, (title, signal, style_name, icon_name) in enumerate(timer_buttons):
            button = QPushButton(title)
            button.setMinimumHeight(52)
            button.setObjectName(style_name)
            button.clicked.connect(lambda _checked=False, current_signal=signal: current_signal.emit())
            self._apply_button_icon_style(button, style_name, icon_name)
            grid.addWidget(button, index // 2, index % 2)
        return widget

    def _apply_button_icon_style(
        self,
        button: QPushButton,
        style_name: str,
        icon_name: str | None,
    ) -> None:
        if not icon_name:
            return

        color_by_style = {
            "AccentButton": "#ffffff",
            "CompactAccentButton": "#ffffff",
            "LargeActionButton": "#ffffff",
            "DangerButton": "#ffffff",
            "SecondaryButton": "#173b86",
            "CompactSecondaryButton": "#173b86",
        }
        apply_button_icon(
            button,
            icon_name,
            color=color_by_style.get(style_name, "#ffffff"),
        )

    def _update_toggle_icon(self, button: QPushButton, icon_name: str, checked: bool) -> None:
        apply_button_icon(
            button,
            icon_name,
            color="#ffffff" if checked else "#173b86",
        )

    def update_context(
        self,
        game: Game | None,
        round_item: Round | None,
        question: Question | None,
        projector_scene: str,
        projector_title: str,
        music_status: str,
        timer_value: str,
        timer_source: str,
        timer_status: str,
    ) -> None:
        if projector_scene in {"round", "question", "answer", "scores", "teams", "winners", "media"}:
            self._game_started = True
            self._apply_started_visibility()
        scene_labels = {
            "welcome": "стартовый экран",
            "waiting": "ожидание / скрытый вопрос",
            "game": "название игры",
            "partner": "спонсорский блок",
            "round": "раунд",
            "question": "вопрос",
            "answer": "правильный ответ",
            "scores": "таблица очков",
            "teams": "команды",
            "winners": "победители",
            "media": "файл игры",
            "empty": "пустой экран",
        }
        self.current_game_label.setText(
            f"Игра: {game.title}" if game is not None else "Игра: не выбрана"
        )
        self.current_round_label.setText(
            f"Раунд: {round_item.title}" if round_item is not None else "Раунд: не выбран"
        )
        self.current_question_label.setText(
            f"Вопрос: {question.title}" if question is not None else "Вопрос: не выбран"
        )
        self.projector_state_label.setText(
            f"Сейчас на проекторе: {scene_labels.get(projector_scene, projector_scene or 'нет активного экрана')}"
        )
        self.music_state_label.setText(music_status or "Фоновая музыка выключена")
        self.timer_value_label.setText(timer_value or "--:--")
        self.timer_source_label.setText(timer_source or "Таймер не подготовлен")
        self.timer_status_label.setText(timer_status or "Статус таймера: не запущен")
        self._sync_screen_toggles(projector_scene, projector_title, bool(music_status))

    def update_dashboard(
        self,
        game: Game | None,
        rounds: list[Round],
        media_assets: list[MediaAsset],
        selected_round: Round | None,
        round_questions: list[Question],
        current_question: Question | None,
        round_completed: bool,
    ) -> None:
        if game is None:
            self._current_dashboard_game_id = None
            self._game_started = False
            self._apply_started_visibility()
        elif game.id != self._current_dashboard_game_id:
            self._current_dashboard_game_id = game.id
            self._game_started = False
            self._apply_started_visibility()

        self._dashboard_questions = list(round_questions)
        self._dashboard_current_question_id = current_question.id if current_question is not None else None
        self._dashboard_round_completed = round_completed
        self._dashboard_media_assets = list(media_assets)
        self._dashboard_rounds = list(rounds)
        self._dashboard_selected_round_id = selected_round.id if selected_round is not None else None

        game_level_media = [
            media
            for media in media_assets
            if media.round_id is None and media.question_id is None
        ]
        self._dashboard_game_level_media = list(game_level_media)
        self._rebuild_media_buttons(game_level_media)
        self._rebuild_round_buttons(rounds, selected_round.id if selected_round is not None else None)
        self._rebuild_question_cards(
            round_questions,
            current_question.id if current_question is not None else None,
            round_completed,
            media_assets,
        )

        if game is None:
            self.start_info_label.setText(
                "Сначала подготовьте игру в конструкторе, затем нажмите «Запустить игру»."
            )
            self.media_state_label.setText("Для этой игры пока нет общих файлов.")
            self.round_state_label.setText("Для этой игры пока нет раундов.")
            self.round_summary_label.setText("Выберите раунд, чтобы увидеть его вопросы.")
            self.round_completion_label.setText("После завершения раунда у вопросов активируется кнопка показа ответа.")
            self.questions_state_label.setText("В выбранном раунде пока нет вопросов.")
            return

        self.start_info_label.setText(
            f"Сейчас идёт игра «{game.title}». Сначала нажмите «Начать игру», затем работайте с раундами и вопросами."
        )
        self.media_state_label.setText(
            "Нажмите на общий файл игры, чтобы сразу вывести его на проектор."
            if game_level_media
            else "Для этой игры пока нет общих файлов верхнего уровня."
        )
        self.round_state_label.setText(
            "Выберите раунд: после этого ниже появится список его вопросов."
            if rounds
            else "Для этой игры пока нет раундов."
        )
        if selected_round is None:
            self.round_summary_label.setText(
                "Название раунда: не выбрано\n"
                "Описание: выберите раунд, чтобы увидеть его описание."
            )
            self.round_completion_label.setText("После завершения раунда у вопросов активируется кнопка показа ответа.")
            self.questions_state_label.setText("После выбора раунда здесь появятся карточки вопросов.")
            return

        self.round_summary_label.setText(
            f"Раунд {selected_round.order_index}. {selected_round.title}\n"
            f"Таймер по умолчанию: "
            f"{selected_round.timer_seconds if selected_round.timer_seconds > 0 else 'без таймера'}\n"
            f"Описание: {selected_round.notes or 'Описание раунда пока не заполнено.'}"
        )
        self.round_completion_label.setText(
            "Раунд завершён. Теперь можно по одному открывать ответы на вопросы."
            if round_completed
            else "Раунд идёт. Показывайте вопросы, запускайте таймер и завершите раунд, когда вопросы закончатся."
        )
        self.questions_state_label.setText(
            (
                "Раунд завершён. Сначала можно снова открыть вопрос, потом отдельно показать ответ."
                if round_completed
                else "Показывайте вопрос, при необходимости запускайте таймер. "
                "Ответ можно открыть только после завершения раунда."
            )
            if round_questions
            else "В этом раунде пока нет вопросов."
        )

    def _rebuild_media_buttons(self, media_assets: list[MediaAsset]) -> None:
        self._clear_layout(self.media_buttons_layout)
        if not media_assets:
            return

        for index, media in enumerate(media_assets):
            button = QPushButton(self._media_button_text(media))
            button.setMinimumHeight(54)
            button.setObjectName("SecondaryButton")
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(
                lambda _checked=False, media_id=media.id: self.show_media_requested.emit(media_id)
            )
            icon_name = {
                "video": "External_Link",
                "image": "Tag",
                "audio": "Link",
            }.get(media.media_type, "Link")
            apply_button_icon(button, icon_name, color="#173b86")
            columns = self._media_button_columns()
            self.media_buttons_layout.addWidget(button, index // columns, index % columns)

    def _rebuild_round_buttons(self, rounds: list[Round], selected_round_id: int | None) -> None:
        self._clear_layout(self.round_buttons_layout)
        if not rounds:
            return

        ordered_rounds = sorted(rounds, key=lambda item: item.order_index)
        for index, round_item in enumerate(ordered_rounds):
            is_selected = round_item.id == selected_round_id
            button = QPushButton(f"{round_item.order_index}. {round_item.title}")
            button.setMinimumHeight(56)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.setObjectName("LargeActionButton" if is_selected else "SecondaryButton")
            button.clicked.connect(
                lambda _checked=False, round_id=round_item.id: self.select_round_by_id_requested.emit(round_id)
            )
            button.clicked.connect(
                lambda _checked=False, round_id=round_item.id: self.show_round_by_id_requested.emit(round_id)
            )
            apply_button_icon(
                button,
                "Book_Open",
                color="#ffffff" if is_selected else "#173b86",
            )
            columns = self._round_button_columns()
            self.round_buttons_layout.addWidget(button, index // columns, index % columns)

    def _rebuild_question_cards(
        self,
        questions: list[Question],
        current_question_id: int | None,
        round_completed: bool,
        media_assets: list[MediaAsset],
    ) -> None:
        self._clear_box_layout(self.questions_cards_layout)
        if not questions:
            self.expanded_question_id = None
            return

        question_media_map: dict[int, list[MediaAsset]] = {}
        answer_media_map: dict[int, list[MediaAsset]] = {}
        option_media_map: dict[int, list[MediaAsset]] = {}
        for media in media_assets:
            if media.question_id is None:
                continue
            if media.usage_role in {"question", "question_image", "question_video", "question_audio"}:
                question_media_map.setdefault(media.question_id, []).append(media)
            elif media.usage_role in {"answer", "answer_image", "answer_video", "answer_audio"}:
                answer_media_map.setdefault(media.question_id, []).append(media)
            elif media.usage_role in {
                "option_a_image",
                "option_b_image",
                "option_c_image",
                "option_d_image",
            }:
                option_media_map.setdefault(media.question_id, []).append(media)

        ordered_questions = sorted(questions, key=lambda item: item.order_index)
        for question in ordered_questions:
            card = QFrame()
            card.setObjectName("ContentCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setSpacing(10)

            meta_label = QLabel(self._question_meta_text(question))
            meta_label.setObjectName("PageHint")
            meta_label.setWordWrap(True)

            summary = QLabel(self._short_text(question.prompt or "Текст вопроса пока не заполнен.", 130))
            summary.setWordWrap(True)
            summary.setObjectName("SectionCaption")

            answer_preview = QLabel(
                f"<span style='color:#6b7280;'>Ответ:</span> "
                f"<span style='font-weight:700; color:#1f2430;'>{escape(question.answer or 'не заполнен')}</span>"
            )
            answer_preview.setWordWrap(True)
            answer_preview.setTextFormat(Qt.RichText)

            options_preview = self._build_options_preview(question)

            question_media_items = sorted(
                question_media_map.get(question.id, []),
                key=lambda item: item.created_at,
            )
            answer_media_items = sorted(
                answer_media_map.get(question.id, []),
                key=lambda item: item.created_at,
            )
            option_media_items = sorted(
                option_media_map.get(question.id, []),
                key=lambda item: item.usage_role,
            )

            if question.id == current_question_id:
                card.setStyleSheet(
                    "QFrame#ContentCard {"
                    "background: #eef4ff;"
                    "border: 1px solid #bfd4ff;"
                    "border-radius: 20px;"
                    "}"
                )

            layout.addWidget(meta_label)
            layout.addWidget(summary)
            layout.addWidget(answer_preview)

            if options_preview is not None:
                layout.addWidget(options_preview)

            buttons = QWidget()
            buttons_layout = QGridLayout(buttons)
            buttons_layout.setContentsMargins(0, 0, 0, 0)
            buttons_layout.setHorizontalSpacing(8)
            buttons_layout.setVerticalSpacing(8)

            actions: list[tuple[str, Signal | None, str, str, int | None]] = []
            if not round_completed:
                actions.append(
                    ("Показать вопрос", self.show_question_by_id_requested, "CompactAccentButton", "Search_Magnifying_Glass", question.id)
                )
                if question.timer_seconds > 0:
                    actions.append(
                        ("Запустить таймер", self.start_timer_for_question_requested, "CompactSecondaryButton", "Check_Big", question.id)
                    )
                if question_media_items:
                    actions.append(
                        (
                            "Медиа вопроса",
                            self.show_question_media_by_id_requested,
                            "CompactSecondaryButton",
                            "External_Link",
                            question.id,
                        )
                    )
            else:
                actions.append(
                    ("Показать вопрос", self.show_question_by_id_requested, "CompactSecondaryButton", "Search_Magnifying_Glass", question.id)
                )
                if question_media_items:
                    actions.append(
                        (
                            "Медиа вопроса",
                            self.show_question_media_by_id_requested,
                            "CompactSecondaryButton",
                            "External_Link",
                            question.id,
                        )
                    )
                actions.append(
                    ("Показать ответ", self.show_answer_by_id_requested, "CompactAccentButton", "Check_Big", question.id)
                )
                if answer_media_items:
                    actions.append(
                        (
                            "Медиа ответа",
                            self.show_answer_media_by_id_requested,
                            "CompactSecondaryButton",
                            "External_Link",
                            question.id,
                        )
                    )

            actions.append(("Скрыть вопрос", None, "CompactSecondaryButton", "Filter", None))

            columns = self._question_action_columns()
            for index, (title, signal, style_name, icon_name, action_question_id) in enumerate(actions):
                button = QPushButton(title)
                button.setMinimumHeight(40)
                button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                button.setObjectName(style_name)
                if signal is None:
                    button.clicked.connect(lambda _checked=False: self.hide_question_requested.emit())
                else:
                    button.clicked.connect(
                        lambda _checked=False, question_id=action_question_id, current_signal=signal: current_signal.emit(question_id)  # type: ignore[arg-type]
                    )
                self._apply_button_icon_style(button, style_name, icon_name)
                buttons_layout.addWidget(button, index // columns, index % columns)
            layout.addWidget(buttons)
            self.questions_cards_layout.addWidget(card)
        self.questions_cards_layout.addStretch(1)

    @staticmethod
    def _media_button_text(media: MediaAsset) -> str:
        prefix = {
            "video": "Показать видео",
            "image": "Показать картинку",
            "audio": "Включить аудио",
        }.get(media.media_type, "Показать файл")
        role_suffix = {
            "game_splash": "Заставка",
            "rules": "Правила",
            "waiting_background": "Ожидание",
            "pause": "Пауза",
            "sponsor": "Партнёры",
            "background_music": "Музыка",
        }.get(media.usage_role)
        if role_suffix:
            return f"{prefix}\n{role_suffix}: {media.title}"
        return f"{prefix}\n{media.title}"

    @staticmethod
    def _question_media_action_title(media: MediaAsset) -> str:
        return {
            "question": "Показать медиа",
            "question_image": "Показать картинку",
            "question_video": "Показать видео",
            "question_audio": "Включить аудио",
            "answer": "Показать медиа ответа",
            "answer_image": "Показать картинку ответа",
            "answer_video": "Показать видео ответа",
            "answer_audio": "Включить аудио ответа",
            "option_a_image": "Картинка A",
            "option_b_image": "Картинка B",
            "option_c_image": "Картинка C",
            "option_d_image": "Картинка D",
        }.get(media.usage_role, media.title)

    @staticmethod
    def _round_type_label(round_type: str) -> str:
        return {
            "standard": "Стандартный",
            "media": "Медиа-раунд",
            "blitz": "Блиц",
            "final": "Финал",
        }.get(round_type, round_type)

    @staticmethod
    def _clear_layout(layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _detach_layout_widgets(layout: QGridLayout) -> None:
        while layout.count():
            layout.takeAt(0)

    @staticmethod
    def _clear_box_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _short_text(text: str, limit: int) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1].rstrip() + "…"

    @staticmethod
    def _question_meta_text(question: Question) -> str:
        parts = [f"Вопрос {question.order_index}", f"Очки: {question.points}"]
        if question.timer_seconds > 0:
            parts.append(f"{question.timer_seconds} сек")
        return "   ".join(parts)

    def _build_options_preview(self, question: Question) -> QLabel | None:
        if question.question_type != "abcd":
            return None

        correct_letter = self._resolve_question_answer_letter(question)
        option_rows: list[str] = []
        for letter, option_text in (
            ("A", question.option_a),
            ("B", question.option_b),
            ("C", question.option_c),
            ("D", question.option_d),
        ):
            is_correct = letter == correct_letter
            option_rows.append(
                "<div style='margin:4px 0;'>"
                f"<span style='display:inline-block; min-width:24px; color:{'#16a34a' if is_correct else '#6b7280'}; font-weight:800;'>{letter}</span> "
                f"<span style='color:{'#166534' if is_correct else '#334155'}; font-weight:{'700' if is_correct else '500'};'>{escape(option_text or '—')}</span>"
                "</div>"
            )

        label = QLabel("".join(option_rows))
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        return label

    @staticmethod
    def _resolve_question_answer_letter(question: Question) -> str:
        raw_answer = (question.answer or "").strip()
        normalized_answer = raw_answer.upper()
        if normalized_answer[:1] in {"A", "B", "C", "D"} and (
            len(normalized_answer) == 1 or normalized_answer[1] in {".", ")", " ", ":"}
        ):
            return normalized_answer[:1]

        for letter, option_text in (
            ("A", question.option_a),
            ("B", question.option_b),
            ("C", question.option_c),
            ("D", question.option_d),
        ):
            if option_text and normalized_answer == option_text.strip().upper():
                return letter
        return ""

    def _sync_screen_toggles(
        self,
        projector_scene: str,
        projector_title: str,
        music_active: bool,
    ) -> None:
        active_states = {
            "splash": projector_scene == "welcome",
            "waiting": projector_scene == "waiting",
            "scores": projector_scene == "scores" and projector_title != "Колонка очков",
            "score_column": projector_scene == "scores" and projector_title == "Колонка очков",
            "qr": projector_scene == "game" and projector_title == "Код подключения игроков",
            "teams": projector_scene == "teams",
            "winners": projector_scene == "winners",
            "sponsor": projector_scene == "partner",
            "music": music_active,
        }
        for key, button in self.screen_toggle_buttons.items():
            should_check = active_states.get(key, False)
            button.blockSignals(True)
            button.setChecked(should_check)
            button.blockSignals(False)
            icon_name = {
                "splash": "Star",
                "waiting": "Link",
                "scores": "Chart_Bar_Vertical_01",
                "score_column": "Chart_Bar_Vertical_01",
                "qr": "Command",
                "teams": "Main_Component",
                "winners": "Check_All_Big",
                "sponsor": "Book_Open",
                "music": "Link",
            }.get(key)
            if icon_name:
                self._update_toggle_icon(button, icon_name, should_check)

    def _handle_game_start_requested(self) -> None:
        self._game_started = True
        self._apply_started_visibility()
        self.show_splash_requested.emit()

    def _apply_started_visibility(self) -> None:
        visible = self._game_started and self._current_dashboard_game_id is not None
        for widget in (
            self.screen_controls_card,
            self.media_card,
            self.rounds_questions_card,
            self.score_card,
        ):
            widget.setVisible(visible)

        self.timer_navigation_card.setVisible(False)
        self.context_card.setVisible(False)

        if hasattr(self, "start_game_button"):
            self.start_game_button.setVisible(self._current_dashboard_game_id is not None)

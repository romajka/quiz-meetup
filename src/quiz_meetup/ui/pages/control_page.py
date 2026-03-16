from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
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

        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        content_layout.addWidget(
            self._build_card(
                "1. Начало игры",
                [
                    self.start_info_label,
                    self._build_button_row(
                        [
                            ("Стартовый экран игры", self.show_splash_requested, "AccentButton", "Star"),
                            ("Открыть окно проектора", self.open_projector_requested, "SecondaryButton", "External_Link"),
                        ]
                    ),
                ],
            )
        )

        content_layout.addWidget(
            self._build_card(
                "2. Управление экраном игры",
                [
                    self._build_button_grid(
                        [
                            ("Показать заставку", self.show_splash_requested, "SecondaryButton", "Star"),
                            ("Показать ожидание", self.show_waiting_requested, "SecondaryButton", "Link"),
                            ("Показать таблицу", self.show_scores_requested, "AccentButton", "Chart_Bar_Vertical_01"),
                            ("Скрыть таблицу", self.hide_scores_requested, "SecondaryButton", "Filter"),
                            ("Показать QR-код", self.show_qr_requested, "SecondaryButton", "Command"),
                            ("Показать колонку очков", self.show_score_column_requested, "SecondaryButton", "Chart_Bar_Vertical_01"),
                            ("Скрыть колонку очков", self.hide_score_column_requested, "SecondaryButton", "Filter"),
                            ("Представить команды", self.show_teams_requested, "SecondaryButton", "Main_Component"),
                            ("Показать победителей", self.show_winners_requested, "SecondaryButton", "Check_All_Big"),
                            ("Спонсорский блок", self.play_sponsor_requested, "SecondaryButton", "Book_Open"),
                            ("Включить музыку", self.play_background_music_requested, "SecondaryButton", "Link"),
                            ("Остановить музыку", self.stop_background_music_requested, "SecondaryButton", "Exit"),
                        ],
                        columns=3,
                        min_height=52,
                    ),
                ],
            )
        )

        content_layout.addWidget(
            self._build_card(
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
        )

        content_layout.addWidget(
            self._build_card(
                "4. Раунды и вопросы",
                [
                    self.round_state_label,
                    self.round_buttons_widget,
                    self.round_summary_label,
                    self._build_button_row(
                        [
                            ("Завершить раунд", self.finish_round_requested, "AccentButton", "Check_All_Big"),
                        ]
                    ),
                    self.round_completion_label,
                    self.questions_state_label,
                    self.questions_cards_widget,
                ],
            )
        )

        content_layout.addWidget(
            self._build_card(
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
        )

        content_layout.addWidget(
            self._build_card(
                "6. Команды и счёт",
                [
                    self.score_hint_label,
                    self._build_button_row(
                        [
                            ("Открыть таблицу очков", self.show_scores_requested, "AccentButton", "Chart_Bar_Vertical_01"),
                            ("Показать победителей", self.show_winners_requested, "SecondaryButton", "Check_All_Big"),
                        ]
                    ),
                ],
            )
        )

        content_layout.addWidget(
            self._build_card(
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
        )
        content_layout.addStretch(1)

        scroll_area.setWidget(content)
        root_layout.addWidget(scroll_area)

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
            "LargeActionButton": "#ffffff",
            "DangerButton": "#ffffff",
            "SecondaryButton": "#173b86",
        }
        apply_button_icon(
            button,
            icon_name,
            color=color_by_style.get(style_name, "#ffffff"),
        )

    def update_context(
        self,
        game: Game | None,
        round_item: Round | None,
        question: Question | None,
        projector_scene: str,
        music_status: str,
        timer_value: str,
        timer_source: str,
        timer_status: str,
    ) -> None:
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
        game_level_media = [
            media
            for media in media_assets
            if media.round_id is None and media.question_id is None
        ]
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
            f"Сейчас идёт игра «{game.title}». Ниже находятся общие экраны, раунды, вопросы и ручное управление."
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
            self.round_summary_label.setText("Сначала выберите раунд.")
            self.round_completion_label.setText("После завершения раунда у вопросов активируется кнопка показа ответа.")
            self.questions_state_label.setText("После выбора раунда здесь появятся карточки вопросов.")
            return

        self.round_summary_label.setText(
            f"Выбран раунд: {selected_round.order_index}. {selected_round.title}\n"
            f"{selected_round.notes or 'Заметка для ведущего пока не заполнена.'}"
        )
        self.round_completion_label.setText(
            "Раунд завершён. Теперь можно по одному открывать ответы на вопросы."
            if round_completed
            else "Раунд идёт. Показывайте вопросы, запускайте таймер и завершите раунд, когда вопросы закончатся."
        )
        self.questions_state_label.setText(
            "Нажмите на карточку вопроса: можно сразу показать вопрос, запустить таймер или открыть ответ."
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
            button.clicked.connect(
                lambda _checked=False, media_id=media.id: self.show_media_requested.emit(media_id)
            )
            icon_name = {
                "video": "External_Link",
                "image": "Tag",
                "audio": "Link",
            }.get(media.media_type, "Link")
            apply_button_icon(button, icon_name, color="#173b86")
            self.media_buttons_layout.addWidget(button, index // 4, index % 4)

    def _rebuild_round_buttons(self, rounds: list[Round], selected_round_id: int | None) -> None:
        self._clear_layout(self.round_buttons_layout)
        if not rounds:
            return

        ordered_rounds = sorted(rounds, key=lambda item: item.order_index)
        for index, round_item in enumerate(ordered_rounds):
            is_selected = round_item.id == selected_round_id
            button = QPushButton(f"{round_item.order_index}. {round_item.title}")
            button.setMinimumHeight(56)
            button.setObjectName("LargeActionButton" if is_selected else "SecondaryButton")
            button.clicked.connect(
                lambda _checked=False, round_id=round_item.id: self.show_round_by_id_requested.emit(round_id)
            )
            apply_button_icon(
                button,
                "Book_Open",
                color="#ffffff" if is_selected else "#173b86",
            )
            self.round_buttons_layout.addWidget(button, index // 4, index % 4)

    def _rebuild_question_cards(
        self,
        questions: list[Question],
        current_question_id: int | None,
        round_completed: bool,
        media_assets: list[MediaAsset],
    ) -> None:
        self._clear_box_layout(self.questions_cards_layout)
        if not questions:
            return

        question_media_map = {
            media.question_id: media
            for media in media_assets
            if media.question_id is not None and media.usage_role == "question"
        }
        answer_media_map = {
            media.question_id: media
            for media in media_assets
            if media.question_id is not None and media.usage_role == "answer"
        }

        ordered_questions = sorted(questions, key=lambda item: item.order_index)
        for question in ordered_questions:
            card = QFrame()
            card.setObjectName("ContentCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setSpacing(10)

            type_label = "ABCD" if question.question_type == "abcd" else "Открытый"
            header = QLabel(
                f"Вопрос {question.order_index} · {type_label} · {question.points} очк. · "
                f"{question.timer_seconds if question.timer_seconds > 0 else 0} сек"
            )
            header.setObjectName("SectionCaption")

            prompt = QLabel(question.prompt or "Текст вопроса пока не заполнен.")
            prompt.setWordWrap(True)

            answer_preview = QLabel(f"Ответ: {question.answer or 'не заполнен'}")
            answer_preview.setWordWrap(True)

            options_preview = None
            if question.question_type == "abcd":
                options_preview = QLabel(
                    "Варианты:\n"
                    f"A. {question.option_a or '—'}\n"
                    f"B. {question.option_b or '—'}\n"
                    f"C. {question.option_c or '—'}\n"
                    f"D. {question.option_d or '—'}"
                )
                options_preview.setWordWrap(True)
                options_preview.setObjectName("DetailsLabel")

            question_media = question_media_map.get(question.id)
            answer_media = answer_media_map.get(question.id)
            media_preview = QLabel(
                f"Медиа вопроса: {question_media.title if question_media is not None else 'не прикреплено'}\n"
                f"Медиа ответа: {answer_media.title if answer_media is not None else 'не прикреплено'}"
            )
            media_preview.setWordWrap(True)
            media_preview.setObjectName("DetailsLabel")

            if question.id == current_question_id:
                card.setStyleSheet(
                    "QFrame#ContentCard {"
                    "background: #eef4ff;"
                    "border: 1px solid #bfd4ff;"
                    "border-radius: 20px;"
                    "}"
                )

            buttons = QWidget()
            buttons_layout = QGridLayout(buttons)
            buttons_layout.setContentsMargins(0, 0, 0, 0)
            buttons_layout.setHorizontalSpacing(8)
            buttons_layout.setVerticalSpacing(8)

            button_specs = [
                ("Показать вопрос", self.show_question_by_id_requested, "SecondaryButton", "Search_Magnifying_Glass"),
                ("Запустить таймер", self.start_timer_for_question_requested, "SecondaryButton", "Check_Big"),
                ("Пауза таймера", self.pause_timer_for_question_requested, "SecondaryButton", "Filter"),
                ("Сброс таймера", self.reset_timer_for_question_requested, "SecondaryButton", "Trash_Empty"),
                ("Больше не принимать ответы", self.stop_answers_for_question_requested, "SecondaryButton", "Filter"),
                ("Показать медиа вопроса", self.show_question_media_by_id_requested, "SecondaryButton", "External_Link"),
                ("Показать медиа ответа", self.show_answer_media_by_id_requested, "SecondaryButton", "External_Link"),
                ("Показать ответ", self.show_answer_by_id_requested, "AccentButton", "Check_Big"),
                ("Скрыть вопрос", self.hide_question_requested, "SecondaryButton", "Filter"),
            ]

            for index, (title, signal, style_name, icon_name) in enumerate(button_specs):
                button = QPushButton(title)
                button.setMinimumHeight(46)
                button.setObjectName(style_name)
                if title == "Показать ответ":
                    button.setEnabled(round_completed)
                elif title == "Показать медиа вопроса":
                    button.setEnabled(question_media is not None)
                elif title == "Показать медиа ответа":
                    button.setEnabled(answer_media is not None)
                if signal is self.hide_question_requested:
                    button.clicked.connect(lambda _checked=False, current_signal=signal: current_signal.emit())
                else:
                    button.clicked.connect(
                        lambda _checked=False, question_id=question.id, current_signal=signal: current_signal.emit(question_id)
                    )
                self._apply_button_icon_style(button, style_name, icon_name)
                buttons_layout.addWidget(button, index // 3, index % 3)

            layout.addWidget(header)
            layout.addWidget(prompt)
            layout.addWidget(answer_preview)
            if options_preview is not None:
                layout.addWidget(options_preview)
            layout.addWidget(media_preview)
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
        return f"{prefix}\n{media.title}"

    @staticmethod
    def _clear_layout(layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _clear_box_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

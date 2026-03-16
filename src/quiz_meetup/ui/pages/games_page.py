from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QUrl

from quiz_meetup.config import DEFAULT_QUESTION_TIMER_SECONDS, DEFAULT_ROUND_TIMER_SECONDS
from quiz_meetup.models import Game, Question, Round
from quiz_meetup.services.game_service import GameService
from quiz_meetup.services.game_session_service import GameSessionService
from quiz_meetup.services.media_service import MediaService
from quiz_meetup.services.question_service import QuestionService
from quiz_meetup.services.round_service import RoundService
from quiz_meetup.services.team_service import TeamService
from quiz_meetup.ui.icons import apply_button_icon, interface_icon


class GameMediaDropZone(QFrame):
    files_dropped = Signal(list)
    browse_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._drop_enabled = False
        self.setObjectName("GameMediaDropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("dragActive", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(3)

        self.title_label = QLabel("Сначала сохраните игру")
        self.title_label.setObjectName("DropZoneTitle")
        self.hint_label = QLabel("После этого сюда можно перетаскивать файлы.")
        self.hint_label.setObjectName("CompactListMeta")
        self.hint_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.hint_label)

    def set_drop_enabled(self, enabled: bool) -> None:
        self._drop_enabled = enabled
        self.setEnabled(enabled)
        if enabled:
            self.title_label.setText("Перетащите сюда общие файлы")
            self.hint_label.setText("Изображения, видео и аудио добавятся в библиотеку игры.")
        else:
            self.title_label.setText("Сначала сохраните игру")
            self.hint_label.setText("После этого сюда можно перетаскивать файлы.")
        self._refresh_style()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self._drop_enabled and event.button() == Qt.MouseButton.LeftButton:
            self.browse_requested.emit()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._can_accept(event):
            event.acceptProposedAction()
            self.setProperty("dragActive", True)
            self._refresh_style()
            return
        event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent) -> None:
        if self._can_accept(event):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[override]
        self.setProperty("dragActive", False)
        self._refresh_style()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self.setProperty("dragActive", False)
        self._refresh_style()
        if not self._can_accept(event):
            event.ignore()
            return

        file_paths: list[str] = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.exists() and path.is_file():
                file_paths.append(str(path))

        if not file_paths:
            event.ignore()
            return

        self.files_dropped.emit(file_paths)
        event.acceptProposedAction()

    def _can_accept(self, event) -> bool:
        return self._drop_enabled and event.mimeData().hasUrls()

    def _refresh_style(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class GamesPage(QWidget):
    data_changed = Signal()
    selection_changed = Signal()
    autosave_status_changed = Signal(str)
    open_media_requested = Signal()
    edit_round_requested = Signal(int)
    edit_question_requested = Signal(int)
    view_changed = Signal()
    start_game_requested = Signal(int)
    start_new_session_requested = Signal(int)
    continue_session_requested = Signal(int)

    def __init__(
        self,
        game_service: GameService,
        game_session_service: GameSessionService,
        round_service: RoundService,
        question_service: QuestionService,
        media_service: MediaService,
        team_service: TeamService,
    ) -> None:
        super().__init__()
        self.game_service = game_service
        self.game_session_service = game_session_service
        self.round_service = round_service
        self.question_service = question_service
        self.media_service = media_service
        self.team_service = team_service

        self.all_games: list[Game] = []
        self.current_game_id: int | None = None
        self.current_round_id: int | None = None
        self.current_question_id: int | None = None
        self._loading_state = False
        self._pending_autosave_scopes: set[str] = set()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(900)

        self._build_widgets()
        self._build_ui()
        self._connect_signals()
        self._autosave_timer.timeout.connect(self._run_autosave)
        self._update_question_type_ui()
        self._update_editor_state()

    def _build_widgets(self) -> None:
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск игр по названию или описанию")

        self.games_list = QListWidget()
        self.games_list.setObjectName("GamesCatalogList")
        self.games_list.setSpacing(10)
        self.games_list.setMinimumHeight(260)
        self.catalog_hint_label = QLabel(
            "Создайте новую игру или выберите сохранённую игру из списка."
        )
        self.catalog_hint_label.setObjectName("PageHint")
        self.catalog_hint_label.setWordWrap(True)
        self.open_editor_button = QPushButton("Открыть игру")
        self.open_editor_button.setObjectName("AccentButton")
        self.start_game_button = QPushButton("Начать игру")
        self.start_game_button.setObjectName("LargeActionButton")
        self.selected_game_title_label = QLabel("Игра не выбрана")
        self.selected_game_title_label.setObjectName("SectionCaption")
        self.selected_game_summary_label = QLabel(
            "Здесь будет информация о выбранной игре или шаблоне."
        )
        self.selected_game_summary_label.setObjectName("DetailsLabel")
        self.selected_game_summary_label.setWordWrap(True)
        self.selected_game_stats_label = QLabel(
            "Сохраните первую игру, чтобы появились раунды, вопросы и медиа."
        )
        self.selected_game_stats_label.setObjectName("DetailsLabel")
        self.selected_game_stats_label.setWordWrap(True)

        self.mode_label = QLabel("Новая игра")
        self.mode_label.setObjectName("PageHint")

        self.game_title_input = QLineEdit()
        self.game_title_input.setPlaceholderText("Например: Большой городской квиз")

        self.game_description_input = QTextEdit()
        self.game_description_input.setPlaceholderText(
            "Описание игры, настроение, особенности раундов и заметки для ведущего."
        )
        self.game_description_input.setFixedHeight(72)

        self.title_input = self.game_title_input
        self.description_input = self.game_description_input

        self.new_game_button = QPushButton("Создать игру")
        self.new_game_button.setObjectName("AccentButton")
        self.save_game_button = QPushButton("Сохранить игру")
        self.save_game_button.setObjectName("AccentButton")
        self.duplicate_game_button = QPushButton("Создать копию")
        self.duplicate_game_button.setObjectName("SecondaryButton")
        self.delete_game_button = QPushButton("Удалить игру")
        self.delete_game_button.setObjectName("DangerButton")

        self.game_meta_label = QLabel("Выберите игру слева или создайте новую.")
        self.game_meta_label.setObjectName("DetailsLabel")
        self.game_meta_label.setWordWrap(True)
        self.game_stats_label = QLabel("После создания здесь появится сводка по структуре игры.")
        self.game_stats_label.setObjectName("DetailsLabel")
        self.game_stats_label.setWordWrap(True)

        self.rounds_list = QListWidget()
        self.rounds_list.setMinimumHeight(150)
        self.rounds_list.setMaximumHeight(190)
        self.round_title_input = QLineEdit()
        self.round_title_input.setPlaceholderText("Например: Разминка")
        self.round_timer_input = QSpinBox()
        self.round_timer_input.setRange(5, 900)
        self.round_timer_input.setSuffix(" сек")
        self.round_timer_input.setValue(DEFAULT_ROUND_TIMER_SECONDS)
        self.round_notes_input = QTextEdit()
        self.round_notes_input.setPlaceholderText("Подсказки и заметки для ведущего по раунду.")
        self.round_notes_input.setFixedHeight(90)
        self.new_round_button = QPushButton("Новый раунд")
        self.new_round_button.setObjectName("SecondaryButton")
        self.save_round_button = QPushButton("Сохранить раунд")
        self.save_round_button.setObjectName("AccentButton")
        self.round_up_button = QPushButton("Вверх")
        self.round_down_button = QPushButton("Вниз")
        self.delete_round_button = QPushButton("Удалить раунд")
        self.delete_round_button.setObjectName("DangerButton")
        self.round_info_label = QLabel("Сохраните игру, чтобы начать добавлять раунды.")
        self.round_info_label.setObjectName("DetailsLabel")
        self.round_info_label.setWordWrap(True)
        self.round_hint_label = QLabel(
            "Выберите раунд, чтобы увидеть его вопросы."
        )
        self.round_hint_label.setObjectName("PageHint")
        self.round_hint_label.setWordWrap(True)

        self.questions_list = QListWidget()
        self.questions_list.setMinimumHeight(170)
        self.questions_list.setMaximumHeight(220)
        self.question_type_combo = QComboBox()
        self.question_type_combo.addItem("Открытый вопрос", "open")
        self.question_type_combo.addItem("ABCD вопрос", "abcd")
        self.question_prompt_input = QTextEdit()
        self.question_prompt_input.setPlaceholderText("Текст вопроса, который увидят ведущий и проектор.")
        self.question_prompt_input.setFixedHeight(110)
        self.question_points_input = QSpinBox()
        self.question_points_input.setRange(1, 100)
        self.question_points_input.setValue(1)
        self.question_timer_input = QSpinBox()
        self.question_timer_input.setRange(0, 900)
        self.question_timer_input.setSpecialValueText("Без таймера")
        self.question_timer_input.setSuffix(" сек")
        self.question_timer_input.setValue(DEFAULT_QUESTION_TIMER_SECONDS)
        self.question_notes_input = QTextEdit()
        self.question_notes_input.setPlaceholderText("Заметка для ведущего: что проговорить, на что обратить внимание.")
        self.question_notes_input.setFixedHeight(90)

        self.question_answer_stack = QStackedWidget()
        self.open_answer_input = QLineEdit()
        self.open_answer_input.setPlaceholderText("Введите правильный ответ")
        self.abcd_answer_combo = QComboBox()
        self.abcd_answer_combo.addItem("A", "A")
        self.abcd_answer_combo.addItem("B", "B")
        self.abcd_answer_combo.addItem("C", "C")
        self.abcd_answer_combo.addItem("D", "D")
        self.question_answer_stack.addWidget(self.open_answer_input)
        self.question_answer_stack.addWidget(self.abcd_answer_combo)

        self.options_widget = QWidget()
        options_layout = QFormLayout(self.options_widget)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(8)
        self.option_a_input = QLineEdit()
        self.option_b_input = QLineEdit()
        self.option_c_input = QLineEdit()
        self.option_d_input = QLineEdit()
        self.option_a_input.setPlaceholderText("Вариант A")
        self.option_b_input.setPlaceholderText("Вариант B")
        self.option_c_input.setPlaceholderText("Вариант C")
        self.option_d_input.setPlaceholderText("Вариант D")
        options_layout.addRow("A", self.option_a_input)
        options_layout.addRow("B", self.option_b_input)
        options_layout.addRow("C", self.option_c_input)
        options_layout.addRow("D", self.option_d_input)

        self.new_question_button = QPushButton("Новый вопрос")
        self.new_question_button.setObjectName("SecondaryButton")
        self.save_question_button = QPushButton("Сохранить вопрос")
        self.save_question_button.setObjectName("AccentButton")
        self.question_up_button = QPushButton("Вверх")
        self.question_down_button = QPushButton("Вниз")
        self.delete_question_button = QPushButton("Удалить вопрос")
        self.delete_question_button.setObjectName("DangerButton")
        self.question_info_label = QLabel("Сначала выберите или создайте раунд.")
        self.question_info_label.setObjectName("DetailsLabel")
        self.question_info_label.setWordWrap(True)
        self.question_hint_label = QLabel(
            "Здесь показаны вопросы выбранного раунда."
        )
        self.question_hint_label.setObjectName("PageHint")
        self.question_hint_label.setWordWrap(True)
        self.question_media_info_label = QLabel(
            "Медиа вопроса пока не прикреплено. Можно добавить изображение, видео или аудио."
        )
        self.question_media_info_label.setObjectName("DetailsLabel")
        self.question_media_info_label.setWordWrap(True)
        self.add_question_media_button = QPushButton("Добавить или выбрать файл")
        self.add_question_media_button.setObjectName("SecondaryButton")
        self.open_question_media_button = QPushButton("Открыть файл вопроса")
        self.open_question_media_button.setObjectName("SecondaryButton")
        self.remove_question_media_button = QPushButton("Удалить файл вопроса")
        self.remove_question_media_button.setObjectName("DangerButton")
        self.answer_media_info_label = QLabel(
            "Медиа ответа пока не прикреплено. Можно добавить изображение, видео или аудио."
        )
        self.answer_media_info_label.setObjectName("DetailsLabel")
        self.answer_media_info_label.setWordWrap(True)
        self.add_answer_media_button = QPushButton("Добавить или выбрать файл")
        self.add_answer_media_button.setObjectName("SecondaryButton")
        self.open_answer_media_button = QPushButton("Открыть файл ответа")
        self.open_answer_media_button.setObjectName("SecondaryButton")
        self.remove_answer_media_button = QPushButton("Удалить файл ответа")
        self.remove_answer_media_button.setObjectName("DangerButton")
        self.back_to_games_button = QPushButton("Назад к списку игр")
        self.back_to_games_button.setObjectName("SecondaryButton")
        self.open_media_button = QPushButton("Открыть медиа")
        self.open_media_button.setObjectName("SecondaryButton")
        self.media_hint_label = QLabel(
            "Загрузите сюда общие файлы, если они будут использоваться в игре. Желательно наименуйте их."
        )
        self.media_hint_label.setObjectName("DetailsLabel")
        self.media_hint_label.setWordWrap(True)
        self.editor_step_label = QLabel(
            "Краткая информация по игре."
        )
        self.editor_step_label.setObjectName("PageHint")
        self.editor_step_label.setWordWrap(True)
        self.game_mode_label = QLabel(
            "Ведущий вручную показывает вопросы, ответы и выставляет баллы."
        )
        self.game_mode_label.setObjectName("DetailsLabel")
        self.game_mode_label.setWordWrap(True)
        self.game_media_state_label = QLabel(
            "Пока нет общих файлов."
        )
        self.game_media_state_label.setObjectName("DetailsLabel")
        self.game_media_state_label.setWordWrap(True)
        self.game_media_drop_zone = GameMediaDropZone()
        self.game_media_buttons_widget = QWidget()
        self.game_media_buttons_layout = QGridLayout(self.game_media_buttons_widget)
        self.game_media_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.game_media_buttons_layout.setHorizontalSpacing(8)
        self.game_media_buttons_layout.setVerticalSpacing(8)

        self._apply_button_sizes()
        self._apply_icons()

    def _apply_button_sizes(self) -> None:
        for button in (
            self.new_game_button,
            self.save_game_button,
            self.duplicate_game_button,
            self.delete_game_button,
            self.new_round_button,
            self.save_round_button,
            self.round_up_button,
            self.round_down_button,
            self.delete_round_button,
            self.new_question_button,
            self.save_question_button,
            self.question_up_button,
            self.question_down_button,
            self.delete_question_button,
            self.open_editor_button,
            self.start_game_button,
            self.back_to_games_button,
            self.open_media_button,
            self.add_question_media_button,
            self.open_question_media_button,
            self.remove_question_media_button,
            self.add_answer_media_button,
            self.open_answer_media_button,
            self.remove_answer_media_button,
        ):
            button.setMinimumHeight(46)

    def _apply_icons(self) -> None:
        apply_button_icon(self.new_game_button, "Check_Big", color="#ffffff")
        apply_button_icon(self.save_game_button, "Check_Big", color="#ffffff")
        apply_button_icon(self.start_game_button, "External_Link", color="#ffffff")
        apply_button_icon(self.open_editor_button, "Book_Open", color="#ffffff")
        apply_button_icon(self.duplicate_game_button, "Check_All_Big", color="#173b86")
        apply_button_icon(self.delete_game_button, "Trash_Full", color="#ffffff")
        apply_button_icon(self.back_to_games_button, "Link", color="#173b86")
        apply_button_icon(self.open_media_button, "External_Link", color="#173b86")
        apply_button_icon(self.new_round_button, "Book", color="#173b86")
        apply_button_icon(self.save_round_button, "Check_Big", color="#ffffff")
        apply_button_icon(self.delete_round_button, "Trash_Full", color="#ffffff")
        apply_button_icon(self.new_question_button, "Search_Magnifying_Glass", color="#173b86")
        apply_button_icon(self.save_question_button, "Check_Big", color="#ffffff")
        apply_button_icon(self.delete_question_button, "Trash_Full", color="#ffffff")
        apply_button_icon(self.add_question_media_button, "Download", color="#173b86")
        apply_button_icon(self.open_question_media_button, "External_Link", color="#173b86")
        apply_button_icon(self.remove_question_media_button, "Trash_Full", color="#ffffff")
        apply_button_icon(self.add_answer_media_button, "Download", color="#173b86")
        apply_button_icon(self.open_answer_media_button, "External_Link", color="#173b86")
        apply_button_icon(self.remove_answer_media_button, "Trash_Full", color="#ffffff")

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(16)

        self.content_stack = QStackedWidget()
        self.dashboard_page = self._build_dashboard_page()
        self.editor_page = self._build_editor_page()
        self.content_stack.addWidget(self.dashboard_page)
        self.content_stack.addWidget(self.editor_page)

        root_layout.addWidget(self.content_stack)

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        hero_card = QFrame()
        hero_card.setObjectName("ContentCard")
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(22, 22, 22, 22)
        hero_layout.setSpacing(18)

        hero_text_layout = QVBoxLayout()
        hero_text_layout.setSpacing(8)
        title = QLabel("Мои игры")
        title.setObjectName("PageTitle")
        hero_text_layout.addWidget(title)
        hero_text_layout.addWidget(self.catalog_hint_label)
        hero_text_layout.addWidget(
            QLabel(
                "Здесь хранятся шаблоны игр. Сначала соберите игру: "
                "раунды, вопросы и общие медиа. Затем запускайте новую "
                "игровую сессию или продолжайте уже начатую."
            )
        )

        hero_actions_layout = QVBoxLayout()
        hero_actions_layout.setSpacing(10)
        hero_actions_layout.addWidget(self.new_game_button)
        hero_actions_layout.addWidget(self.search_input)
        hero_actions_layout.addStretch(1)

        hero_layout.addLayout(hero_text_layout, 3)
        hero_layout.addLayout(hero_actions_layout, 2)

        layout.addWidget(hero_card)
        layout.addWidget(self._build_games_catalog_card(), 1)
        return page

    def _build_games_catalog_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Список игр")
        title.setObjectName("SectionCaption")
        layout.addWidget(title)
        layout.addWidget(QLabel("Откройте игру для редактирования, запустите новую игровую сессию или продолжите текущую."))
        layout.addWidget(self.games_list, 1)
        return card

    def _build_game_summary_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)
        layout.addWidget(QLabel("Выбранная игра"))
        layout.addWidget(self.selected_game_title_label)
        layout.addWidget(self.selected_game_summary_label)
        layout.addWidget(self.selected_game_stats_label)
        layout.addWidget(self.open_editor_button)
        layout.addWidget(self.duplicate_game_button)
        layout.addWidget(self.delete_game_button)
        layout.addWidget(self.start_game_button)
        layout.addStretch(1)
        return card

    def _build_editor_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        content_layout.addWidget(self._build_editor_header_card())
        content_layout.addWidget(self._build_game_details_card())
        content_layout.addWidget(self._build_media_hint_card())
        content_layout.addWidget(self._build_rounds_card())
        content_layout.addWidget(self._build_questions_card())
        content_layout.addStretch(1)
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)
        return page

    def _build_editor_header_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)
        title = QLabel("Редактор игры")
        title.setObjectName("PageTitle")
        text_layout.addWidget(title)
        text_layout.addWidget(self.editor_step_label)

        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(10)
        actions_layout.addWidget(self.back_to_games_button)
        actions_layout.addStretch(1)

        layout.addLayout(text_layout, 1)
        layout.addLayout(actions_layout)
        return card

    def _build_media_hint_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        title = QLabel("Общие файлы игры")
        title.setObjectName("SectionCaption")
        layout.addWidget(title)
        layout.addWidget(self.media_hint_label)
        layout.addWidget(self.game_media_drop_zone)
        layout.addWidget(self.game_media_state_label)
        layout.addWidget(self.game_media_buttons_widget)
        layout.addWidget(self.open_media_button)
        return card

    def _build_game_mode_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        title = QLabel("Режим игры")
        title.setObjectName("SectionCaption")
        layout.addWidget(title)
        layout.addWidget(self.game_mode_label)
        return card

    def _build_question_media_card(
        self,
        title_text: str,
        info_label: QLabel,
        add_button: QPushButton,
        open_button: QPushButton,
        remove_button: QPushButton,
    ) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(title_text)
        title.setObjectName("SectionCaption")
        layout.addWidget(title)
        layout.addWidget(info_label)

        buttons_layout = QGridLayout()
        buttons_layout.setHorizontalSpacing(8)
        buttons_layout.setVerticalSpacing(8)
        buttons_layout.addWidget(add_button, 0, 0)
        buttons_layout.addWidget(open_button, 0, 1)
        buttons_layout.addWidget(remove_button, 1, 0, 1, 2)
        layout.addLayout(buttons_layout)
        return card

    def _build_game_details_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)
        buttons_row.addWidget(self.save_game_button)
        buttons_row.addStretch(1)

        layout.addLayout(buttons_row)
        layout.addWidget(self.game_title_input)
        layout.addWidget(self.game_description_input)
        layout.addWidget(self.game_meta_label)
        layout.addWidget(self.game_stats_label)
        return card

    def _build_rounds_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Раунды игры")
        title.setObjectName("SectionCaption")
        layout.addWidget(title)
        layout.addWidget(self.round_hint_label)
        layout.addWidget(self.rounds_list, 1)
        return card

    def _build_questions_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("Вопросы раунда")
        title.setObjectName("SectionCaption")
        layout.addWidget(title)
        layout.addWidget(self.question_hint_label)
        layout.addWidget(self.questions_list, 1)
        return card

    def _connect_signals(self) -> None:
        self.search_input.textChanged.connect(lambda _text: self._rebuild_games_list())
        self.games_list.itemSelectionChanged.connect(self._handle_game_selection_changed)
        self.games_list.itemDoubleClicked.connect(
            lambda _item: self.open_selected_game()
        )
        self.rounds_list.itemSelectionChanged.connect(self._handle_round_selection_changed)
        self.questions_list.itemSelectionChanged.connect(self._handle_question_selection_changed)
        self.question_type_combo.currentIndexChanged.connect(
            lambda _index: self._update_question_type_ui()
        )

        self.new_game_button.clicked.connect(self.start_new_game)
        self.open_editor_button.clicked.connect(self.open_selected_game)
        self.start_game_button.clicked.connect(self._start_selected_game)
        self.back_to_games_button.clicked.connect(self.show_dashboard)
        self.open_media_button.clicked.connect(self._open_media_for_current_game)
        self.game_media_drop_zone.files_dropped.connect(self._import_game_media_files)
        self.game_media_drop_zone.browse_requested.connect(self._browse_common_media_files)
        self.add_question_media_button.clicked.connect(
            lambda: self._attach_media_to_current_question("question")
        )
        self.open_question_media_button.clicked.connect(
            lambda: self._open_current_question_media("question")
        )
        self.remove_question_media_button.clicked.connect(
            lambda: self._remove_current_question_media("question")
        )
        self.add_answer_media_button.clicked.connect(
            lambda: self._attach_media_to_current_question("answer")
        )
        self.open_answer_media_button.clicked.connect(
            lambda: self._open_current_question_media("answer")
        )
        self.remove_answer_media_button.clicked.connect(
            lambda: self._remove_current_question_media("answer")
        )
        self.save_game_button.clicked.connect(self._save_game)
        self.duplicate_game_button.clicked.connect(self._duplicate_game)
        self.delete_game_button.clicked.connect(self._delete_game)

        self.new_round_button.clicked.connect(self.start_new_round)
        self.save_round_button.clicked.connect(self._save_round)
        self.round_up_button.clicked.connect(self._move_round_up)
        self.round_down_button.clicked.connect(self._move_round_down)
        self.delete_round_button.clicked.connect(self._delete_round)

        self.new_question_button.clicked.connect(self.start_new_question)
        self.save_question_button.clicked.connect(self._save_question)
        self.question_up_button.clicked.connect(self._move_question_up)
        self.question_down_button.clicked.connect(self._move_question_down)
        self.delete_question_button.clicked.connect(self._delete_question)

        self.game_title_input.textChanged.connect(lambda _text: self._schedule_autosave("game"))
        self.game_description_input.textChanged.connect(lambda: self._schedule_autosave("game"))
        self.round_title_input.textChanged.connect(lambda _text: self._schedule_autosave("round"))
        self.round_notes_input.textChanged.connect(lambda: self._schedule_autosave("round"))
        self.question_type_combo.currentIndexChanged.connect(
            lambda _index: self._schedule_autosave("question")
        )
        self.question_prompt_input.textChanged.connect(lambda: self._schedule_autosave("question"))
        self.question_points_input.valueChanged.connect(lambda _value: self._schedule_autosave("question"))
        self.question_timer_input.valueChanged.connect(lambda _value: self._schedule_autosave("question"))
        self.question_notes_input.textChanged.connect(lambda: self._schedule_autosave("question"))
        self.open_answer_input.textChanged.connect(lambda _text: self._schedule_autosave("question"))
        self.abcd_answer_combo.currentIndexChanged.connect(
            lambda _index: self._schedule_autosave("question")
        )
        self.option_a_input.textChanged.connect(lambda _text: self._schedule_autosave("question"))
        self.option_b_input.textChanged.connect(lambda _text: self._schedule_autosave("question"))
        self.option_c_input.textChanged.connect(lambda _text: self._schedule_autosave("question"))
        self.option_d_input.textChanged.connect(lambda _text: self._schedule_autosave("question"))

    def refresh(self, preferred_game_id: int | None = None) -> None:
        self.flush_autosave()
        self._loading_state = True
        preferred_round_id = self.current_round_id
        preferred_question_id = self.current_question_id
        self.all_games = self.game_service.list_games()
        self._rebuild_games_list(
            preferred_game_id=preferred_game_id if preferred_game_id is not None else self.current_game_id,
            preferred_round_id=preferred_round_id,
            preferred_question_id=preferred_question_id,
        )
        self._loading_state = False

    def show_dashboard(self) -> None:
        self.content_stack.setCurrentWidget(self.dashboard_page)
        self.view_changed.emit()

    def show_editor(self) -> None:
        self.content_stack.setCurrentWidget(self.editor_page)
        self.view_changed.emit()

    def is_dashboard_visible(self) -> bool:
        return self.content_stack.currentWidget() is self.dashboard_page

    def is_editor_visible(self) -> bool:
        return self.content_stack.currentWidget() is self.editor_page

    def header_context(self) -> tuple[str, str]:
        if self.is_editor_visible():
            if self.current_game_id is None:
                return (
                    "Новая игра",
                    "Сначала сохраните игру, затем настраивайте раунды, вопросы, медиа и команды.",
                )

            game = self.get_selected_game()
            game_title = game.title if game is not None else "Редактор игры"
            return (
                game_title,
                "Сейчас открыт редактор этой игры. Все действия ниже относятся только к ней.",
            )

        return (
            "Мои игры",
            "Список готовых игр и вход в режим подготовки новой игры.",
        )

    def start_new_game(self) -> None:
        self.flush_autosave()
        self._loading_state = True
        self.current_game_id = None
        self.current_round_id = None
        self.current_question_id = None
        self.games_list.blockSignals(True)
        self.games_list.clearSelection()
        self.games_list.blockSignals(False)

        self.mode_label.setText("Новая игра")
        self.game_title_input.clear()
        self.game_description_input.clear()
        self.game_meta_label.setText(
            "Введите название и описание игры, затем сохраните её."
        )
        self.game_stats_label.setText(
            "После сохранения можно добавлять раунды и вопросы."
        )
        self._clear_round_form()
        self._clear_question_form()
        self.rounds_list.clear()
        self.questions_list.clear()
        self._update_game_media_overview(None)
        self._set_dashboard_game_state(None)
        self._update_editor_state()
        self.autosave_status_changed.emit("Автосохранение: новая игра будет создана вручную")
        self._loading_state = False
        self.show_editor()
        self.selection_changed.emit()

    def open_selected_game(self) -> None:
        if self.current_game_id is None:
            QMessageBox.warning(self, "Игры", "Сначала выберите игру из списка.")
            return
        self.show_editor()

    def _start_selected_game(self) -> None:
        game = self.get_selected_game()
        if game is None:
            QMessageBox.warning(self, "Игры", "Сначала выберите игру из списка.")
            return
        self.start_new_session_requested.emit(game.id)

    def _continue_selected_game(self) -> None:
        game = self.get_selected_game()
        if game is None:
            QMessageBox.warning(self, "Игры", "Сначала выберите игру из списка.")
            return

        active_session = self.game_session_service.get_active_session(game.id)
        if active_session is None:
            QMessageBox.warning(self, "Игры", "У этой игры пока нет активной сессии.")
            return
        self.continue_session_requested.emit(active_session.id)

    def _open_media_for_current_game(self) -> None:
        if self.current_game_id is None:
            QMessageBox.warning(self, "Игры", "Сначала сохраните или выберите игру.")
            return
        self.open_media_requested.emit()

    def start_new_round(self) -> None:
        if self.current_game_id is None:
            QMessageBox.warning(self, "Раунды", "Сначала сохраните игру.")
            return
        self.flush_autosave()
        self._loading_state = True
        self.current_round_id = None
        self.current_question_id = None
        self.rounds_list.blockSignals(True)
        self.rounds_list.clearSelection()
        self.rounds_list.blockSignals(False)
        self.questions_list.clear()
        self._clear_round_form()
        self._clear_question_form()
        self.round_info_label.setText("Заполните форму и сохраните новый раунд.")
        self.question_info_label.setText("Сначала сохраните или выберите раунд.")
        self._update_editor_state()
        self.autosave_status_changed.emit("Автосохранение: новый раунд будет создан вручную")
        self._loading_state = False
        self.selection_changed.emit()

    def start_new_question(self) -> None:
        if self.current_round_id is None:
            QMessageBox.warning(self, "Вопросы", "Сначала выберите или создайте раунд.")
            return
        self.flush_autosave()
        self._loading_state = True
        self.current_question_id = None
        self.questions_list.blockSignals(True)
        self.questions_list.clearSelection()
        self.questions_list.blockSignals(False)
        self._clear_question_form()
        self.question_info_label.setText("Заполните форму и сохраните вопрос.")
        self._update_editor_state()
        self.autosave_status_changed.emit("Автосохранение: новый вопрос будет создан вручную")
        self._loading_state = False
        self.selection_changed.emit()

    def get_selected_game(self) -> Game | None:
        if self.current_game_id is None:
            return None
        return self.game_service.get_game(self.current_game_id)

    def get_selected_round(self) -> Round | None:
        if self.current_round_id is None:
            return None
        return self.round_service.get_round(self.current_round_id)

    def get_selected_question(self) -> Question | None:
        if self.current_question_id is None:
            return None
        return self.question_service.get_question(self.current_question_id)

    def select_next_question(self) -> Question | None:
        return self._navigate_question(step=1)

    def select_previous_question(self) -> Question | None:
        return self._navigate_question(step=-1)

    def _save_game(self) -> None:
        try:
            if self.current_game_id is None:
                game = self.game_service.create_game(
                    title=self.game_title_input.text(),
                    description=self.game_description_input.toPlainText(),
                )
            else:
                game = self.game_service.update_game(
                    game_id=self.current_game_id,
                    title=self.game_title_input.text(),
                    description=self.game_description_input.toPlainText(),
                )
        except ValueError as error:
            QMessageBox.warning(self, "Игры", str(error))
            return

        self.current_game_id = game.id
        self.refresh(preferred_game_id=game.id)
        self.data_changed.emit()

    def _duplicate_game(self) -> None:
        self.flush_autosave()
        game = self.get_selected_game()
        if game is None:
            QMessageBox.warning(self, "Игры", "Сначала выберите игру для дублирования.")
            return

        try:
            duplicated_game = self.game_service.duplicate_game(game.id)
        except ValueError as error:
            QMessageBox.warning(self, "Игры", str(error))
            return

        self.current_game_id = duplicated_game.id
        self.current_round_id = None
        self.current_question_id = None
        self.refresh(preferred_game_id=duplicated_game.id)
        self.data_changed.emit()

    def _delete_game(self) -> None:
        self.flush_autosave()
        game = self.get_selected_game()
        if game is None:
            QMessageBox.warning(self, "Игры", "Сначала выберите игру для удаления.")
            return

        answer = QMessageBox.question(
            self,
            "Удаление игры",
            f"Удалить игру «{game.title}» вместе со всеми раундами и вопросами?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.game_service.delete_game(game.id)
        except ValueError as error:
            QMessageBox.warning(self, "Игры", str(error))
            return

        self.current_game_id = None
        self.current_round_id = None
        self.current_question_id = None
        self.refresh()
        self.data_changed.emit()

    def _save_round(self) -> None:
        if self.current_game_id is None:
            QMessageBox.warning(self, "Раунды", "Сначала сохраните игру.")
            return

        try:
            if self.current_round_id is None:
                round_item = self.round_service.create_round(
                    game_id=self.current_game_id,
                    title=self.round_title_input.text(),
                    order_index=None,
                    timer_seconds=DEFAULT_ROUND_TIMER_SECONDS,
                    notes=self.round_notes_input.toPlainText(),
                )
            else:
                current_round = self.get_selected_round()
                round_item = self.round_service.update_round(
                    round_id=self.current_round_id,
                    title=self.round_title_input.text(),
                    timer_seconds=current_round.timer_seconds if current_round is not None else DEFAULT_ROUND_TIMER_SECONDS,
                    notes=self.round_notes_input.toPlainText(),
                )
        except ValueError as error:
            QMessageBox.warning(self, "Раунды", str(error))
            return

        self.current_round_id = round_item.id
        self.refresh(preferred_game_id=self.current_game_id)
        self._select_round(round_item.id)
        self.data_changed.emit()

    def _delete_round(self) -> None:
        self.flush_autosave()
        round_item = self.get_selected_round()
        if round_item is None:
            QMessageBox.warning(self, "Раунды", "Сначала выберите раунд.")
            return

        answer = QMessageBox.question(
            self,
            "Удаление раунда",
            f"Удалить раунд «{round_item.title}» вместе со всеми вопросами?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.round_service.delete_round(round_item.id)
        except ValueError as error:
            QMessageBox.warning(self, "Раунды", str(error))
            return

        self.current_round_id = None
        self.current_question_id = None
        self.refresh(preferred_game_id=self.current_game_id)
        self.data_changed.emit()

    def _move_round_up(self) -> None:
        self._move_round(self.round_service.move_round_up)

    def _move_round_down(self) -> None:
        self._move_round(self.round_service.move_round_down)

    def _move_round(self, action) -> None:
        self.flush_autosave()
        round_item = self.get_selected_round()
        if round_item is None:
            QMessageBox.warning(self, "Раунды", "Сначала выберите раунд.")
            return

        try:
            action(round_item.id)
        except ValueError as error:
            QMessageBox.warning(self, "Раунды", str(error))
            return

        self.refresh(preferred_game_id=self.current_game_id)
        self._select_round(round_item.id)
        self.data_changed.emit()

    def _save_question(self) -> None:
        if self.current_round_id is None:
            QMessageBox.warning(self, "Вопросы", "Сначала выберите раунд.")
            return

        question_type = self.question_type_combo.currentData()
        answer = (
            self.open_answer_input.text()
            if question_type == "open"
            else str(self.abcd_answer_combo.currentData())
        )

        try:
            if self.current_question_id is None:
                question = self.question_service.create_question(
                    round_id=self.current_round_id,
                    title=None,
                    prompt=self.question_prompt_input.toPlainText(),
                    question_type=question_type,
                    notes=self.question_notes_input.toPlainText(),
                    answer=answer,
                    option_a=self.option_a_input.text(),
                    option_b=self.option_b_input.text(),
                    option_c=self.option_c_input.text(),
                    option_d=self.option_d_input.text(),
                    points=self.question_points_input.value(),
                    order_index=None,
                    timer_seconds=self.question_timer_input.value(),
                )
            else:
                question = self.question_service.update_question(
                    question_id=self.current_question_id,
                    title=None,
                    prompt=self.question_prompt_input.toPlainText(),
                    question_type=question_type,
                    notes=self.question_notes_input.toPlainText(),
                    answer=answer,
                    option_a=self.option_a_input.text(),
                    option_b=self.option_b_input.text(),
                    option_c=self.option_c_input.text(),
                    option_d=self.option_d_input.text(),
                    points=self.question_points_input.value(),
                    timer_seconds=self.question_timer_input.value(),
                )
        except ValueError as error:
            QMessageBox.warning(self, "Вопросы", str(error))
            return

        self.current_question_id = question.id
        self.refresh(preferred_game_id=self.current_game_id)
        self._select_round(question.round_id)
        self._select_question(question.id)
        self.data_changed.emit()

    def _delete_question(self) -> None:
        self.flush_autosave()
        question = self.get_selected_question()
        if question is None:
            QMessageBox.warning(self, "Вопросы", "Сначала выберите вопрос.")
            return

        answer = QMessageBox.question(
            self,
            "Удаление вопроса",
            "Удалить выбранный вопрос?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.question_service.delete_question(question.id)
        except ValueError as error:
            QMessageBox.warning(self, "Вопросы", str(error))
            return

        self.current_question_id = None
        self.refresh(preferred_game_id=self.current_game_id)
        self._select_round(question.round_id)
        self.data_changed.emit()

    def _move_question_up(self) -> None:
        self._move_question(self.question_service.move_question_up)

    def _move_question_down(self) -> None:
        self._move_question(self.question_service.move_question_down)

    def _move_question(self, action) -> None:
        self.flush_autosave()
        question = self.get_selected_question()
        if question is None:
            QMessageBox.warning(self, "Вопросы", "Сначала выберите вопрос.")
            return

        try:
            action(question.id)
        except ValueError as error:
            QMessageBox.warning(self, "Вопросы", str(error))
            return

        self.refresh(preferred_game_id=self.current_game_id)
        self._select_round(question.round_id)
        self._select_question(question.id)
        self.data_changed.emit()

    def _rebuild_games_list(
        self,
        preferred_game_id: int | None = None,
        preferred_round_id: int | None = None,
        preferred_question_id: int | None = None,
    ) -> None:
        query = self.search_input.text().strip().lower()
        filtered_games = [
            game
            for game in self.all_games
            if not query
            or query in game.title.lower()
            or query in game.description.lower()
        ]

        self.games_list.blockSignals(True)
        self.games_list.clear()
        for game in filtered_games:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, game.id)
            item.setSizeHint(QSize(0, 112))
            self.games_list.addItem(item)
            self.games_list.setItemWidget(item, self._build_game_card(game))
        self.games_list.blockSignals(False)

        if self.games_list.count() == 0:
            self.current_game_id = None
            self.current_round_id = None
            self.current_question_id = None
            self._clear_round_form()
            self._clear_question_form()
            self.rounds_list.clear()
            self.questions_list.clear()
            self.mode_label.setText("Новая игра")
            self.game_title_input.clear()
            self.game_description_input.clear()
            self.game_meta_label.setText("Выберите игру на главном экране или создайте новую.")
            self.game_stats_label.setText("После создания здесь появятся раунды, вопросы и медиа.")
            self._update_game_media_overview(None)
            self._update_question_media_state()
            self._set_dashboard_game_state(None)
            self._update_editor_state()
            self.show_dashboard()
            return

        target_row = 0
        if preferred_game_id is not None:
            for index in range(self.games_list.count()):
                if self.games_list.item(index).data(Qt.UserRole) == preferred_game_id:
                    target_row = index
                    break

        self.games_list.setCurrentRow(target_row)
        self._handle_game_selection_changed(
            preferred_round_id=preferred_round_id,
            preferred_question_id=preferred_question_id,
        )
        self._refresh_game_card_selection_styles()

    def _handle_game_selection_changed(
        self,
        preferred_round_id: int | None = None,
        preferred_question_id: int | None = None,
    ) -> None:
        self.flush_autosave()
        self._loading_state = True
        item = self.games_list.currentItem()
        if item is None:
            self.current_game_id = None
            self.game_title_input.clear()
            self.game_description_input.clear()
            self.mode_label.setText("Новая игра")
            self.current_round_id = None
            self.current_question_id = None
            self.rounds_list.clear()
            self.questions_list.clear()
            self._clear_round_form()
            self._clear_question_form()
            self._update_game_media_overview(None)
            self._update_question_media_state()
            self._set_dashboard_game_state(None)
            self._update_editor_state()
            self._loading_state = False
            self.view_changed.emit()
            return

        game_id = item.data(Qt.UserRole)
        game = self.game_service.get_game(game_id)
        if game is None:
            self.current_game_id = None
            self._set_dashboard_game_state(None)
            self._loading_state = False
            return

        self.current_game_id = game.id
        self.game_title_input.setText(game.title)
        self.game_description_input.setPlainText(game.description)
        self.mode_label.setText("Редактирование игры")
        self._update_game_overview(game)
        self._update_game_media_overview(game)
        self._load_rounds(preferred_round_id=preferred_round_id, preferred_question_id=preferred_question_id)
        self._update_editor_state()
        self.autosave_status_changed.emit("Автосохранение: активно")
        self._loading_state = False
        self._refresh_game_card_selection_styles()
        self.view_changed.emit()
        self.selection_changed.emit()

    def _load_rounds(
        self,
        preferred_round_id: int | None = None,
        preferred_question_id: int | None = None,
    ) -> None:
        self.rounds_list.blockSignals(True)
        self.rounds_list.clear()

        game = self.get_selected_game()
        rounds = self.round_service.list_rounds_by_game(game.id) if game is not None else []
        for round_item in rounds:
            question_count = len(self.question_service.list_questions_by_round(round_item.id))
            item = QListWidgetItem()
            item.setData(Qt.UserRole, round_item.id)
            item.setSizeHint(QSize(0, 60))
            self.rounds_list.addItem(item)
            self.rounds_list.setItemWidget(
                item,
                self._build_round_item_widget(item, round_item, question_count),
            )
        self.rounds_list.blockSignals(False)

        if not rounds:
            self.current_round_id = None
            self.current_question_id = None
            self._clear_round_form()
            self.questions_list.clear()
            self._clear_question_form()
            self.round_info_label.setText("Добавьте первый раунд для этой игры.")
            self.question_info_label.setText("Сначала создайте раунд.")
            self._update_editor_state()
            return

        target_row = 0
        target_round_id = preferred_round_id if preferred_round_id is not None else self.current_round_id
        if target_round_id is not None:
            for index in range(self.rounds_list.count()):
                if self.rounds_list.item(index).data(Qt.UserRole) == target_round_id:
                    target_row = index
                    break
        self.rounds_list.setCurrentRow(target_row)
        self._handle_round_selection_changed(preferred_question_id=preferred_question_id)
        self._refresh_inline_selection_styles(self.rounds_list)

    def _handle_round_selection_changed(
        self,
        preferred_question_id: int | None = None,
    ) -> None:
        self.flush_autosave()
        self._loading_state = True
        item = self.rounds_list.currentItem()
        if item is None:
            self.current_round_id = None
            self._clear_round_form()
            self.questions_list.clear()
            self._clear_question_form()
            self._update_editor_state()
            self._loading_state = False
            self._refresh_inline_selection_styles(self.rounds_list)
            self.selection_changed.emit()
            return

        round_id = item.data(Qt.UserRole)
        round_item = self.round_service.get_round(round_id)
        if round_item is None:
            self.current_round_id = None
            self._loading_state = False
            self.selection_changed.emit()
            return

        self.current_round_id = round_item.id
        self.round_title_input.setText(round_item.title)
        self.round_notes_input.setPlainText(round_item.notes)
        self._set_round_info_label(round_item)
        self._load_questions(preferred_question_id=preferred_question_id)
        self._update_editor_state()
        self._loading_state = False
        self._refresh_inline_selection_styles(self.rounds_list)
        self.selection_changed.emit()

    def _load_questions(self, preferred_question_id: int | None = None) -> None:
        self.questions_list.blockSignals(True)
        self.questions_list.clear()

        round_item = self.get_selected_round()
        questions = (
            self.question_service.list_questions_by_round(round_item.id)
            if round_item is not None
            else []
        )
        for question in questions:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, question.id)
            item.setSizeHint(QSize(0, 72))
            self.questions_list.addItem(item)
            self.questions_list.setItemWidget(
                item,
                self._build_question_item_widget(item, question),
            )
        self.questions_list.blockSignals(False)

        if not questions:
            self.current_question_id = None
            self._clear_question_form()
            self.question_info_label.setText("Добавьте первый вопрос в выбранный раунд.")
            self._update_editor_state()
            return

        target_row = 0
        target_question_id = (
            preferred_question_id if preferred_question_id is not None else self.current_question_id
        )
        if target_question_id is not None:
            for index in range(self.questions_list.count()):
                if self.questions_list.item(index).data(Qt.UserRole) == target_question_id:
                    target_row = index
                    break
        self.questions_list.setCurrentRow(target_row)
        self._handle_question_selection_changed()
        self._refresh_inline_selection_styles(self.questions_list)

    def _handle_question_selection_changed(self) -> None:
        self.flush_autosave()
        self._loading_state = True
        item = self.questions_list.currentItem()
        if item is None:
            self.current_question_id = None
            self._clear_question_form()
            self._update_editor_state()
            self._loading_state = False
            self._refresh_inline_selection_styles(self.questions_list)
            self.selection_changed.emit()
            return

        question_id = item.data(Qt.UserRole)
        question = self.question_service.get_question(question_id)
        if question is None:
            self.current_question_id = None
            self._loading_state = False
            self.selection_changed.emit()
            return

        self.current_question_id = question.id
        type_index = self.question_type_combo.findData(question.question_type)
        if type_index >= 0:
            self.question_type_combo.setCurrentIndex(type_index)
        self.question_prompt_input.setPlainText(question.prompt)
        self.question_points_input.setValue(question.points)
        self.question_timer_input.setValue(question.timer_seconds)
        self.question_notes_input.setPlainText(question.notes)
        self.open_answer_input.setText(question.answer if question.question_type == "open" else "")
        abcd_index = self.abcd_answer_combo.findData(question.answer.upper())
        if abcd_index >= 0:
            self.abcd_answer_combo.setCurrentIndex(abcd_index)
        self.option_a_input.setText(question.option_a)
        self.option_b_input.setText(question.option_b)
        self.option_c_input.setText(question.option_c)
        self.option_d_input.setText(question.option_d)
        self._update_question_type_ui()
        self._update_question_media_state()
        self._set_question_info_label(question)
        self._update_editor_state()
        self._loading_state = False
        self._refresh_inline_selection_styles(self.questions_list)
        self.selection_changed.emit()

    def _select_round(self, round_id: int | None) -> None:
        if round_id is None:
            return
        for index in range(self.rounds_list.count()):
            if self.rounds_list.item(index).data(Qt.UserRole) == round_id:
                self.rounds_list.setCurrentRow(index)
                self._handle_round_selection_changed(preferred_question_id=self.current_question_id)
                break

    def _select_question(self, question_id: int | None) -> None:
        if question_id is None:
            return
        for index in range(self.questions_list.count()):
            if self.questions_list.item(index).data(Qt.UserRole) == question_id:
                self.questions_list.setCurrentRow(index)
                self._handle_question_selection_changed()
                break

    def _update_game_overview(self, game: Game) -> None:
        rounds = self.round_service.list_rounds_by_game(game.id)
        questions_count = 0
        for round_item in rounds:
            questions_count += len(self.question_service.list_questions_by_round(round_item.id))
        media_count = len(self.media_service.list_media_by_game(game.id))
        teams_count = len(self.team_service.list_teams_by_game(game.id))

        description = game.description.strip() if game.description else ""
        self.game_meta_label.setText(description or "Без описания.")
        self.game_stats_label.setText(
            f"Раундов: {len(rounds)} · Вопросов: {questions_count} · Файлов: {media_count} · Команд: {teams_count} · Ручное проведение"
        )
        self._set_dashboard_game_state(
            game,
            rounds_count=len(rounds),
            questions_count=questions_count,
            media_count=media_count,
            teams_count=teams_count,
        )

    def _set_dashboard_game_state(
        self,
        game: Game | None,
        rounds_count: int = 0,
        questions_count: int = 0,
        media_count: int = 0,
        teams_count: int = 0,
    ) -> None:
        if game is None:
            self.selected_game_title_label.setText("Игра не выбрана")
            self.selected_game_summary_label.setText(
                "Нажмите «Создать игру», чтобы открыть новый шаблон, или выберите игру из списка."
            )
            self.selected_game_stats_label.setText(
                "Сначала соберите игру в редакторе. "
                "Когда она будет готова, возвращайтесь сюда и запускайте её как отдельный игровой сценарий."
            )
            return

        self.selected_game_title_label.setText(game.title)
        active_session = self.game_session_service.get_active_session(game.id)
        self.selected_game_summary_label.setText(
            game.description or "Описание пока не заполнено. Откройте редактор и добавьте описание игры."
        )
        self.selected_game_stats_label.setText(
            f"Раундов: {rounds_count}\n"
            f"Вопросов: {questions_count}\n"
            f"Медиа: {media_count}\n"
            f"Команд: {teams_count}\n\n"
            + (
                f"Активная сессия: запуск #{active_session.session_number}\n\n"
                if active_session is not None
                else ""
            )
            + "Эту игру можно открыть в редакторе, начать новую сессию или продолжить текущую."
        )

    def _build_game_card(self, game: Game) -> QWidget:
        rounds = self.round_service.list_rounds_by_game(game.id)
        questions_count = sum(
            len(self.question_service.list_questions_by_round(round_item.id))
            for round_item in rounds
        )
        active_session = self.game_session_service.get_active_session(game.id)
        sessions = self.game_session_service.list_sessions_by_game(game.id)
        previous_sessions_count = max(0, len(sessions) - (1 if active_session is not None else 0))
        active_session_teams_count = (
            len(self.team_service.list_teams_by_session(active_session.id))
            if active_session is not None
            else 0
        )

        card = QFrame()
        card.setObjectName("GameListCard")
        card.setProperty("selected", game.id == self.current_game_id)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        badge = QLabel()
        badge.setObjectName("GameCardBadge")
        badge.setFixedSize(58, 58)
        badge_icon = interface_icon("Command", color="#ffffff", size=28)
        badge.setPixmap(badge_icon.pixmap(28, 28))
        badge.setAlignment(Qt.AlignCenter)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        title_label = QLabel(game.title)
        title_label.setObjectName("GameCardTitle")
        title_label.setWordWrap(True)

        meta_label = QLabel(
            f"{len(rounds)} раундов • {questions_count} вопросов • "
            f"{game.updated_at.split('T')[0] if 'T' in game.updated_at else game.updated_at}"
        )
        meta_label.setObjectName("GameCardMeta")
        meta_label.setWordWrap(True)

        info_layout.addWidget(title_label)
        info_layout.addWidget(meta_label)
        if active_session is not None:
            session_label = QLabel(
                f"Текущий запуск игры: #{active_session.session_number} • "
                f"{self._format_session_date(active_session.started_at)} • "
                f"Команд: {active_session_teams_count}"
            )
            session_label.setObjectName("GameCardMeta")
            session_label.setWordWrap(True)
            info_layout.addWidget(session_label)
        elif previous_sessions_count > 0:
            history_label = QLabel(f"Прошлых запусков: {previous_sessions_count}")
            history_label.setObjectName("GameCardMeta")
            history_label.setWordWrap(True)
            info_layout.addWidget(history_label)

        layout.addWidget(badge)
        layout.addLayout(info_layout, 1)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        open_button = QPushButton("Открыть")
        open_button.setObjectName("CardPrimaryButton")
        open_button.setMinimumHeight(48)
        apply_button_icon(open_button, "Book_Open", color="#ffffff")
        open_button.clicked.connect(
            lambda _checked=False, game_id=game.id: self._open_game_from_catalog(game_id)
        )

        start_button = QPushButton("Запустить новую игру")
        start_button.setObjectName("CardStartButton")
        start_button.setMinimumHeight(48)
        apply_button_icon(start_button, "External_Link", color="#ffffff")
        start_button.clicked.connect(
            lambda _checked=False, game_id=game.id: self._start_new_session_from_catalog(game_id)
        )

        continue_button = QPushButton("Продолжить игру")
        continue_button.setObjectName("CardPrimaryButton")
        continue_button.setMinimumHeight(48)
        apply_button_icon(continue_button, "Link", color="#ffffff")
        continue_button.setEnabled(active_session is not None)
        continue_button.clicked.connect(
            lambda _checked=False, game_id=game.id, session_id=active_session.id if active_session is not None else 0: self._continue_session_from_catalog(game_id, session_id)
        )

        copy_button = QPushButton()
        copy_button.setObjectName("CardIconButton")
        copy_button.setFixedSize(48, 48)
        apply_button_icon(copy_button, "Check_All_Big", color="#2f3542")
        copy_button.clicked.connect(
            lambda _checked=False, game_id=game.id: self._duplicate_game_from_catalog(game_id)
        )

        delete_button = QPushButton()
        delete_button.setObjectName("CardDeleteButton")
        delete_button.setFixedSize(48, 48)
        apply_button_icon(delete_button, "Trash_Full", color="#dc2626")
        delete_button.clicked.connect(
            lambda _checked=False, game_id=game.id: self._delete_game_from_catalog(game_id)
        )

        actions_layout.addWidget(open_button)
        actions_layout.addWidget(continue_button)
        actions_layout.addWidget(start_button)
        actions_layout.addWidget(copy_button)
        actions_layout.addWidget(delete_button)
        layout.addLayout(actions_layout)
        return card

    def _select_game_by_id(self, game_id: int) -> None:
        for index in range(self.games_list.count()):
            item = self.games_list.item(index)
            if item.data(Qt.UserRole) == game_id:
                self.games_list.setCurrentItem(item)
                return

    def _open_game_from_catalog(self, game_id: int) -> None:
        self._select_game_by_id(game_id)
        self.open_selected_game()

    def _start_new_session_from_catalog(self, game_id: int) -> None:
        self._select_game_by_id(game_id)
        self._start_selected_game()

    def _continue_session_from_catalog(self, game_id: int, session_id: int) -> None:
        self._select_game_by_id(game_id)
        if session_id <= 0:
            QMessageBox.warning(self, "Игры", "У этой игры пока нет активной сессии.")
            return
        self.continue_session_requested.emit(session_id)

    def _duplicate_game_from_catalog(self, game_id: int) -> None:
        self._select_game_by_id(game_id)
        self._duplicate_game()

    def _delete_game_from_catalog(self, game_id: int) -> None:
        self._select_game_by_id(game_id)
        self._delete_game()

    def _refresh_game_card_selection_styles(self) -> None:
        current_item = self.games_list.currentItem()
        current_game_id = current_item.data(Qt.UserRole) if current_item is not None else None
        for index in range(self.games_list.count()):
            item = self.games_list.item(index)
            widget = self.games_list.itemWidget(item)
            if widget is None:
                continue
            widget.setProperty("selected", item.data(Qt.UserRole) == current_game_id)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def _update_game_media_overview(self, game: Game | None) -> None:
        self._clear_grid_layout(self.game_media_buttons_layout)
        if game is None:
            self.game_media_state_label.setText(
                "Сначала сохраните игру."
            )
            return

        game_level_media = [
            media
            for media in self.media_service.list_media_by_game(game.id)
            if media.round_id is None and media.question_id is None
        ]
        if not game_level_media:
            self.game_media_state_label.setText(
                "Пока нет общих файлов."
            )
            return

        self.game_media_state_label.setText(
            f"Общих файлов: {len(game_level_media)}"
        )
        for index, media in enumerate(game_level_media):
            button = QPushButton(self._game_media_button_text(media))
            button.setMinimumHeight(40)
            button.setObjectName("SecondaryButton")
            button.clicked.connect(
                lambda _checked=False, path=media.file_path: self._open_local_media_preview(path)
            )
            icon_name = {
                "video": "External_Link",
                "image": "Tag",
                "audio": "Link",
            }.get(media.media_type, "Link")
            apply_button_icon(button, icon_name, color="#173b86")
            self.game_media_buttons_layout.addWidget(button, index // 4, index % 4)

    @staticmethod
    def _format_session_date(raw_value: str) -> str:
        if "T" in raw_value:
            return raw_value.replace("T", " ")
        return raw_value

    def _set_round_info_label(self, round_item: Round) -> None:
        self.round_info_label.setText(
            f"Выбран раунд: {round_item.title}"
        )

    def _set_question_info_label(self, question: Question) -> None:
        self.question_info_label.setText(
            f"Выбран вопрос: {question.title}"
        )

    @staticmethod
    def _game_media_button_text(media) -> str:
        return media.title

    def _open_local_media_preview(self, file_path: str) -> None:
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)):
            QMessageBox.warning(self, "Медиа", "Не удалось открыть файл системным приложением.")

    @staticmethod
    def _clear_grid_layout(layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _update_question_media_state(self) -> None:
        question_media = self._get_current_question_media("question")
        answer_media = self._get_current_question_media("answer")

        self.question_media_info_label.setText(
            self._media_label_text(
                question_media,
                empty_text="Медиа вопроса пока не прикреплено. Можно добавить изображение, видео или аудио.",
            )
        )
        self.answer_media_info_label.setText(
            self._media_label_text(
                answer_media,
                empty_text="Медиа ответа пока не прикреплено. Можно добавить изображение, видео или аудио.",
            )
        )

    def _update_question_type_ui(self) -> None:
        question_type = self.question_type_combo.currentData()
        is_abcd = question_type == "abcd"
        self.question_answer_stack.setCurrentIndex(1 if is_abcd else 0)
        self.options_widget.setVisible(is_abcd)

    def _update_editor_state(self) -> None:
        has_game = self.current_game_id is not None
        has_round = self.current_round_id is not None
        has_question = self.current_question_id is not None

        self.open_editor_button.setEnabled(has_game)
        self.start_game_button.setEnabled(has_game)
        self.duplicate_game_button.setEnabled(has_game)
        self.delete_game_button.setEnabled(has_game)
        self.open_media_button.setEnabled(has_game)
        self.game_media_drop_zone.set_drop_enabled(has_game)

        self.round_title_input.setEnabled(has_game)
        self.round_notes_input.setEnabled(has_game)
        self.new_round_button.setEnabled(has_game)
        self.save_round_button.setEnabled(has_game)
        self.round_up_button.setEnabled(has_round)
        self.round_down_button.setEnabled(has_round)
        self.delete_round_button.setEnabled(has_round)

        self.questions_list.setEnabled(has_round)
        self.question_type_combo.setEnabled(has_round)
        self.question_prompt_input.setEnabled(has_round)
        self.question_points_input.setEnabled(has_round)
        self.question_timer_input.setEnabled(has_round)
        self.question_notes_input.setEnabled(has_round)
        self.question_answer_stack.setEnabled(has_round)
        self.options_widget.setEnabled(has_round)
        self.new_question_button.setEnabled(has_round)
        self.save_question_button.setEnabled(has_round)
        self.question_up_button.setEnabled(has_question)
        self.question_down_button.setEnabled(has_question)
        self.delete_question_button.setEnabled(has_question)
        self.add_question_media_button.setEnabled(has_round)
        self.add_answer_media_button.setEnabled(has_round)
        self.open_question_media_button.setEnabled(self._get_current_question_media("question") is not None)
        self.remove_question_media_button.setEnabled(self._get_current_question_media("question") is not None)
        self.open_answer_media_button.setEnabled(self._get_current_question_media("answer") is not None)
        self.remove_answer_media_button.setEnabled(self._get_current_question_media("answer") is not None)

        self.save_game_button.setText("Сохранить игру" if has_game else "Создать игру")
        self.save_round_button.setText("Сохранить раунд" if has_round else "Создать раунд")
        self.save_question_button.setText("Сохранить вопрос" if has_question else "Создать вопрос")
        self.save_game_button.setEnabled(True)
        self.save_round_button.setEnabled(has_game)
        self.save_question_button.setEnabled(has_round)

    def _clear_round_form(self) -> None:
        self.round_title_input.clear()
        self.round_notes_input.clear()

    def _clear_question_form(self) -> None:
        self.question_type_combo.setCurrentIndex(0)
        self.question_prompt_input.clear()
        self.question_points_input.setValue(1)
        self.question_timer_input.setValue(DEFAULT_QUESTION_TIMER_SECONDS)
        self.question_notes_input.clear()
        self.open_answer_input.clear()
        self.abcd_answer_combo.setCurrentIndex(0)
        self.option_a_input.clear()
        self.option_b_input.clear()
        self.option_c_input.clear()
        self.option_d_input.clear()
        self._update_question_type_ui()
        self._update_question_media_state()

    def _question_preview(self, prompt: str) -> str:
        normalized = " ".join(prompt.split())
        return normalized[:64] + ("..." if len(normalized) > 64 else "")

    def _build_round_item_widget(
        self,
        item: QListWidgetItem,
        round_item: Round,
        question_count: int,
    ) -> QWidget:
        card = QFrame()
        card.setObjectName("CompactListCard")
        card.setProperty("selected", False)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title = QLabel(f"{round_item.order_index}. {round_item.title}")
        title.setObjectName("CompactListTitle")
        meta = QLabel(f"Вопросов: {question_count}")
        meta.setObjectName("CompactListMeta")
        text_layout.addWidget(title)
        text_layout.addWidget(meta)

        edit_button = QPushButton()
        edit_button.setObjectName("CardIconButton")
        edit_button.setFixedSize(36, 36)
        apply_button_icon(edit_button, "Book_Open", color="#2f3542")

        def select_item(_event=None) -> None:
            self.rounds_list.setCurrentItem(item)

        def edit_round(_checked: bool = False) -> None:
            self.rounds_list.setCurrentItem(item)
            self.edit_round_requested.emit(round_item.id)

        card.mousePressEvent = select_item
        title.mousePressEvent = select_item
        meta.mousePressEvent = select_item
        edit_button.clicked.connect(edit_round)

        layout.addLayout(text_layout, 1)
        layout.addWidget(edit_button)
        return card

    def _build_question_item_widget(
        self,
        item: QListWidgetItem,
        question: Question,
    ) -> QWidget:
        card = QFrame()
        card.setObjectName("CompactListCard")
        card.setProperty("selected", False)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title = QLabel(f"{question.order_index}. {question.title}")
        title.setObjectName("CompactListTitle")
        meta = QLabel(
            f"{self._question_preview(question.prompt)} · {question.points} очк. · {self._question_timer_label(question.timer_seconds)}"
        )
        meta.setObjectName("CompactListMeta")
        text_layout.addWidget(title)
        text_layout.addWidget(meta)

        edit_button = QPushButton()
        edit_button.setObjectName("CardIconButton")
        edit_button.setFixedSize(36, 36)
        apply_button_icon(edit_button, "Book_Open", color="#2f3542")

        def select_item(_event=None) -> None:
            self.questions_list.setCurrentItem(item)

        def edit_question(_checked: bool = False) -> None:
            self.questions_list.setCurrentItem(item)
            self.edit_question_requested.emit(question.id)

        card.mousePressEvent = select_item
        title.mousePressEvent = select_item
        meta.mousePressEvent = select_item
        edit_button.clicked.connect(edit_question)

        layout.addLayout(text_layout, 1)
        layout.addWidget(edit_button)
        return card

    def _refresh_inline_selection_styles(self, list_widget: QListWidget) -> None:
        current_item = list_widget.currentItem()
        current_id = current_item.data(Qt.UserRole) if current_item is not None else None
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            widget = list_widget.itemWidget(item)
            if widget is None:
                continue
            widget.setProperty("selected", item.data(Qt.UserRole) == current_id)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def _question_timer_label(self, timer_seconds: int) -> str:
        if timer_seconds <= 0:
            return "без таймера"
        return f"{timer_seconds} сек"

    def flush_autosave(self) -> None:
        if self._loading_state or not self._pending_autosave_scopes:
            return
        self._autosave_timer.stop()
        self._run_autosave()

    def _schedule_autosave(self, scope: str) -> None:
        if self._loading_state:
            return
        if scope == "game" and self.current_game_id is None:
            return
        if scope == "round" and self.current_round_id is None:
            return
        if scope == "question" and self.current_question_id is None:
            return

        self._pending_autosave_scopes.add(scope)
        self.autosave_status_changed.emit("Автосохранение: сохранение...")
        self._autosave_timer.start()

    def _run_autosave(self) -> None:
        if self._loading_state or not self._pending_autosave_scopes:
            return

        messages: list[str] = []
        for scope in ("game", "round", "question"):
            if scope not in self._pending_autosave_scopes:
                continue
            status_message = self._autosave_scope(scope)
            if status_message:
                messages.append(status_message)

        self._pending_autosave_scopes.clear()
        if messages:
            self.autosave_status_changed.emit(messages[-1])

    def _autosave_scope(self, scope: str) -> str | None:
        if scope == "game":
            return self._autosave_game()
        if scope == "round":
            return self._autosave_round()
        if scope == "question":
            return self._autosave_question()
        return None

    def _autosave_game(self) -> str:
        if self.current_game_id is None:
            return "Автосохранение: новая игра ещё не создана"

        title = self.game_title_input.text().strip()
        if not title:
            return "Автосохранение: введите название игры"

        try:
            game = self.game_service.update_game(
                game_id=self.current_game_id,
                title=self.game_title_input.text(),
                description=self.game_description_input.toPlainText(),
            )
        except ValueError:
            return "Автосохранение: игра ждёт корректных данных"

        self._update_current_game_list_item(game)
        self._update_game_overview(game)
        self.selection_changed.emit()
        return f"Автосохранение: игра сохранена в {self._current_time_label()}"

    def _autosave_round(self) -> str:
        if self.current_round_id is None:
            return "Автосохранение: новый раунд ещё не создан"

        title = self.round_title_input.text().strip()
        if not title:
            return "Автосохранение: введите название раунда"

        try:
            round_item = self.round_service.update_round(
                round_id=self.current_round_id,
                title=self.round_title_input.text(),
                timer_seconds=DEFAULT_ROUND_TIMER_SECONDS,
                notes=self.round_notes_input.toPlainText(),
            )
        except ValueError:
            return "Автосохранение: раунд ждёт корректных данных"

        self._update_current_round_list_item(round_item)
        self._set_round_info_label(round_item)
        return f"Автосохранение: раунд сохранён в {self._current_time_label()}"

    def _autosave_question(self) -> str:
        if self.current_question_id is None:
            return "Автосохранение: новый вопрос ещё не создан"

        question_type = self.question_type_combo.currentData()
        answer = (
            self.open_answer_input.text()
            if question_type == "open"
            else str(self.abcd_answer_combo.currentData())
        )

        try:
            question = self.question_service.update_question(
                question_id=self.current_question_id,
                title=None,
                prompt=self.question_prompt_input.toPlainText(),
                question_type=question_type,
                notes=self.question_notes_input.toPlainText(),
                answer=answer,
                option_a=self.option_a_input.text(),
                option_b=self.option_b_input.text(),
                option_c=self.option_c_input.text(),
                option_d=self.option_d_input.text(),
                points=self.question_points_input.value(),
                timer_seconds=self.question_timer_input.value(),
            )
        except ValueError:
            return "Автосохранение: вопрос ждёт обязательные поля"

        self._update_current_question_list_item(question)
        self._set_question_info_label(question)
        return f"Автосохранение: вопрос сохранён в {self._current_time_label()}"

    def _update_current_game_list_item(self, game: Game) -> None:
        current_item = self.games_list.currentItem()
        if current_item is None:
            return
        preview = game.description[:58] + ("..." if len(game.description) > 58 else "")
        current_item.setText(game.title if not preview else f"{game.title}\n{preview}")

    def _update_current_round_list_item(self, round_item: Round) -> None:
        current_item = self.rounds_list.currentItem()
        if current_item is None:
            return
        question_count = len(self.question_service.list_questions_by_round(round_item.id))
        current_item.setText(
            f"{round_item.order_index}. {round_item.title}\n"
            f"Вопросов: {question_count}"
        )

    def _update_current_question_list_item(self, question: Question) -> None:
        current_item = self.questions_list.currentItem()
        if current_item is None:
            return
        current_item.setText(
            f"{question.order_index}. [{question.question_type.upper()}] "
            f"{self._question_preview(question.prompt)}\n"
            f"Очки: {question.points} | Таймер: {self._question_timer_label(question.timer_seconds)}"
        )

    @staticmethod
    def _current_time_label() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _get_current_question_media(self, usage_role: str):
        if self.current_game_id is None or self.current_question_id is None:
            return None
        return self.media_service.find_media_for_question(
            game_id=self.current_game_id,
            question_id=self.current_question_id,
            usage_role=usage_role,
        )

    def _media_label_text(self, media, empty_text: str) -> str:
        if media is None:
            return empty_text
        return (
            f"Файл: {media.title}\n"
            f"Тип: {self.media_service.role_label(media.usage_role)} / {media.media_type}\n"
            f"Путь: {media.file_path}"
        )

    def _ensure_question_saved_for_media(self) -> bool:
        if self.current_question_id is not None:
            return True
        self._save_question()
        return self.current_question_id is not None

    def _browse_common_media_files(self) -> None:
        if self.current_game_id is None:
            QMessageBox.warning(self, "Общие файлы", "Сначала сохраните игру.")
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите общие файлы игры",
            "",
            "Медиафайлы (*.png *.jpg *.jpeg *.webp *.mp4 *.webm *.mp3 *.wav *.ogg)",
        )
        if not file_paths:
            return
        self._import_game_media_files(file_paths)

    def _import_game_media_files(self, file_paths: list[str]) -> None:
        if self.current_game_id is None:
            QMessageBox.warning(self, "Общие файлы", "Сначала сохраните игру.")
            return

        imported_count = 0
        errors: list[str] = []
        for file_path in file_paths:
            try:
                self.media_service.import_media(
                    game_id=self.current_game_id,
                    title=Path(file_path).stem,
                    source_path=file_path,
                    usage_role="library",
                )
                imported_count += 1
            except ValueError as error:
                errors.append(f"{Path(file_path).name}: {error}")

        if imported_count:
            game = self.get_selected_game()
            if game is not None:
                self._update_game_overview(game)
                self._update_game_media_overview(game)
            self.autosave_status_changed.emit(f"Общие файлы: добавлено {imported_count}")
            self.data_changed.emit()

        if errors and imported_count == 0:
            QMessageBox.warning(self, "Общие файлы", "\n".join(errors[:3]))

    def _attach_media_to_current_question(self, usage_role: str) -> None:
        if self.current_game_id is None or self.current_round_id is None:
            QMessageBox.warning(self, "Медиа", "Сначала создайте игру и выберите раунд.")
            return
        if not self._ensure_question_saved_for_media():
            return

        source_mode = self._prompt_media_source()
        if source_mode is None:
            return

        question = self.get_selected_question()
        if question is None:
            QMessageBox.warning(self, "Медиа", "Не удалось сохранить вопрос перед добавлением файла.")
            return

        if source_mode == "file":
            source_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите медиафайл",
                "",
                "Поддерживаемые файлы (*.png *.jpg *.jpeg *.webp *.mp4 *.webm *.mp3 *.wav *.ogg);;Все файлы (*)",
            )
            if not source_path:
                return

            try:
                self.media_service.set_question_media(
                    game_id=self.current_game_id,
                    question_id=question.id,
                    usage_role=usage_role,
                    source_path=source_path,
                    title=f"{'Вопрос' if usage_role == 'question' else 'Ответ'} — {question.title}",
                )
            except ValueError as error:
                QMessageBox.warning(self, "Медиа", str(error))
                return
        else:
            media = self._choose_existing_media(self.current_game_id, usage_role)
            if media is None:
                return
            try:
                self.media_service.assign_existing_media_to_question(
                    media_id=media.id,
                    question_id=question.id,
                    usage_role=usage_role,
                )
            except ValueError as error:
                QMessageBox.warning(self, "Медиа", str(error))
                return

        self._update_question_media_state()
        self._update_editor_state()
        self.data_changed.emit()

    def _open_current_question_media(self, usage_role: str) -> None:
        media = self._get_current_question_media(usage_role)
        if media is None:
            QMessageBox.warning(self, "Медиа", "Для этого блока файл пока не выбран.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(media.file_path)):
            QMessageBox.warning(self, "Медиа", "Не удалось открыть файл системным приложением.")

    def _remove_current_question_media(self, usage_role: str) -> None:
        if self.current_game_id is None or self.current_question_id is None:
            return
        media = self._get_current_question_media(usage_role)
        if media is None:
            return

        answer = QMessageBox.question(
            self,
            "Удаление медиа",
            f"Удалить файл «{media.title}» из блока {'вопроса' if usage_role == 'question' else 'ответа'}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.media_service.clear_question_media(
            game_id=self.current_game_id,
            question_id=self.current_question_id,
            usage_role=usage_role,
        )
        self._update_question_media_state()
        self._update_editor_state()
        self.data_changed.emit()

    def _navigate_question(self, step: int) -> Question | None:
        if self.current_game_id is None:
            return None

        self.flush_autosave()
        sequence = self._build_question_sequence()
        if not sequence:
            return None

        target_index: int | None = None
        if self.current_question_id is not None:
            for index, (_round_item, question) in enumerate(sequence):
                if question.id == self.current_question_id:
                    candidate_index = index + step
                    if 0 <= candidate_index < len(sequence):
                        target_index = candidate_index
                    else:
                        return None
                    break

        if target_index is None and self.current_round_id is not None:
            round_question_indexes = [
                index
                for index, (round_item, _question) in enumerate(sequence)
                if round_item.id == self.current_round_id
            ]
            if round_question_indexes:
                target_index = round_question_indexes[0] if step > 0 else round_question_indexes[-1]

        if target_index is None:
            target_index = 0 if step > 0 else len(sequence) - 1

        target_round, target_question = sequence[target_index]
        self._select_round(target_round.id)
        self._select_question(target_question.id)
        return self.get_selected_question()

    def _build_question_sequence(self) -> list[tuple[Round, Question]]:
        if self.current_game_id is None:
            return []

        sequence: list[tuple[Round, Question]] = []
        for round_item in self.round_service.list_rounds_by_game(self.current_game_id):
            questions = self.question_service.list_questions_by_round(round_item.id)
            for question in questions:
                sequence.append((round_item, question))
        return sequence

    def _prompt_media_source(self) -> str | None:
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Медиа")
        message_box.setText("Как добавить медиафайл?")
        import_button = message_box.addButton("Загрузить с ПК", QMessageBox.ButtonRole.AcceptRole)
        library_button = message_box.addButton("Выбрать из библиотеки", QMessageBox.ButtonRole.ActionRole)
        message_box.addButton(QMessageBox.StandardButton.Cancel)
        message_box.exec()

        clicked_button = message_box.clickedButton()
        if clicked_button is import_button:
            return "file"
        if clicked_button is library_button:
            return "library"
        return None

    def _choose_existing_media(self, game_id: int, usage_role: str):
        media_assets = self.media_service.list_media_by_game(game_id)
        if not media_assets:
            QMessageBox.warning(self, "Медиа", "Для этой игры пока нет загруженных файлов.")
            return None

        label_map: dict[str, object] = {}
        labels: list[str] = []
        for media in media_assets:
            label = (
                f"#{media.id}  {media.title}  "
                f"[{media.media_type}]  "
                f"{self.media_service.role_label(media.usage_role)}"
            )
            labels.append(label)
            label_map[label] = media

        selected_label, accepted = QInputDialog.getItem(
            self,
            "Выбор файла из библиотеки",
            "Выберите файл для блока "
            + ("вопроса" if usage_role == "question" else "ответа"),
            labels,
            0,
            False,
        )
        if not accepted or not selected_label:
            return None
        return label_map.get(selected_label)

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from quiz_meetup.models import Game, MediaAsset, Question, Round
from quiz_meetup.services.game_service import GameService
from quiz_meetup.services.media_service import MediaService
from quiz_meetup.services.question_service import QuestionService
from quiz_meetup.services.round_service import RoundService


class MediaPage(QWidget):
    data_changed = Signal()

    def __init__(
        self,
        game_service: GameService,
        media_service: MediaService,
        round_service: RoundService,
        question_service: QuestionService,
    ) -> None:
        super().__init__()
        self.game_service = game_service
        self.media_service = media_service
        self.round_service = round_service
        self.question_service = question_service

        self.cached_rounds: list[Round] = []
        self.cached_questions: list[Question] = []

        self._build_widgets()
        self._build_ui()
        self._connect_signals()
        self._update_assignment_visibility(self.import_role_combo, self.import_round_combo, self.import_question_combo)
        self._update_assignment_visibility(self.edit_role_combo, self.edit_round_combo, self.edit_question_combo)

    def _build_widgets(self) -> None:
        self.game_combo = QComboBox()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию файла или назначению")

        self.media_tree = QTreeWidget()
        self.media_tree.setColumnCount(5)
        self.media_tree.setHeaderLabels(
            ["Название", "Тип", "Назначение", "Привязка", "Файл"]
        )
        self.media_tree.setRootIsDecorated(False)
        self.media_tree.setAlternatingRowColors(True)
        self.media_tree.setUniformRowHeights(True)
        self.media_tree.setMinimumHeight(340)

        self.import_title_input = QLineEdit()
        self.import_title_input.setPlaceholderText("Если оставить пустым, будет взято имя файла")
        self.import_path_input = QLineEdit()
        self.import_path_input.setPlaceholderText("Выберите локальный файл")
        self.import_role_combo = self._build_role_combo()
        self.import_round_combo = QComboBox()
        self.import_question_combo = QComboBox()
        self.add_file_button = QPushButton("Добавить файл")
        self.add_file_button.setObjectName("AccentButton")
        self.browse_button = QPushButton("Обзор")
        self.browse_button.setObjectName("SecondaryButton")

        self.selected_title_input = QLineEdit()
        self.edit_role_combo = self._build_role_combo()
        self.edit_round_combo = QComboBox()
        self.edit_question_combo = QComboBox()
        self.save_binding_button = QPushButton("Сохранить привязку")
        self.save_binding_button.setObjectName("AccentButton")
        self.delete_button = QPushButton("Удалить файл")
        self.delete_button.setObjectName("DangerButton")

        self.file_info_label = QLabel("Выберите файл из библиотеки.")
        self.file_info_label.setWordWrap(True)
        self.file_info_label.setObjectName("DetailsLabel")

        self.preview_stack = QStackedWidget()
        self.empty_preview_label = QLabel("Предпросмотр пока недоступен.")
        self.empty_preview_label.setAlignment(Qt.AlignCenter)
        self.empty_preview_label.setObjectName("DetailsLabel")

        self.image_preview_label = QLabel("Изображение")
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setMinimumHeight(260)
        self.image_preview_label.setObjectName("PreviewFrame")

        self.media_preview_label = QLabel(
            "Для аудио и видео используйте кнопку «Просмотреть файл».\n"
            "Файл откроется в системном приложении по умолчанию."
        )
        self.media_preview_label.setAlignment(Qt.AlignCenter)
        self.media_preview_label.setWordWrap(True)
        self.media_preview_label.setObjectName("DetailsLabel")

        self.preview_stack.addWidget(self.empty_preview_label)
        self.preview_stack.addWidget(self.image_preview_label)
        self.preview_stack.addWidget(self.media_preview_label)

        self.preview_button = QPushButton("Просмотреть файл")
        self.preview_button.setObjectName("SecondaryButton")

        self.import_form: QFormLayout | None = None
        self.edit_form: QFormLayout | None = None

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)
        content_layout.addWidget(QLabel("Медиабиблиотека игры"))

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_library_card())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([680, 620])
        content_layout.addWidget(splitter)
        content_layout.addStretch(1)

        scroll_area.setWidget(content)
        root_layout.addWidget(scroll_area)

    def _build_library_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(QLabel("Игра"))
        layout.addWidget(self.game_combo)
        layout.addWidget(self.search_input)
        layout.addWidget(self.media_tree, 1)
        return card

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_import_card())
        layout.addWidget(self._build_selected_media_card(), 1)
        return panel

    def _build_import_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        path_row.addWidget(self.import_path_input, 1)
        path_row.addWidget(self.browse_button)

        self.import_form = QFormLayout()
        self.import_form.setContentsMargins(0, 0, 0, 0)
        self.import_form.setSpacing(10)
        self.import_form.addRow("Название", self.import_title_input)
        self.import_form.addRow("Файл", path_row)
        self.import_form.addRow("Назначение", self.import_role_combo)
        self.import_form.addRow("Раунд", self.import_round_combo)
        self.import_form.addRow("Вопрос", self.import_question_combo)

        layout.addWidget(QLabel("Добавить файл"))
        layout.addLayout(self.import_form)
        layout.addWidget(self.add_file_button)
        return card

    def _build_selected_media_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ContentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self.edit_form = QFormLayout()
        self.edit_form.setContentsMargins(0, 0, 0, 0)
        self.edit_form.setSpacing(10)
        self.edit_form.addRow("Название", self.selected_title_input)
        self.edit_form.addRow("Назначение", self.edit_role_combo)
        self.edit_form.addRow("Раунд", self.edit_round_combo)
        self.edit_form.addRow("Вопрос", self.edit_question_combo)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)
        buttons_row.addWidget(self.save_binding_button)
        buttons_row.addWidget(self.delete_button)

        preview_buttons = QHBoxLayout()
        preview_buttons.setSpacing(10)
        preview_buttons.addWidget(self.preview_button)

        layout.addWidget(QLabel("Выбранный файл"))
        layout.addLayout(self.edit_form)
        layout.addWidget(QLabel("Информация"))
        layout.addWidget(self.file_info_label)
        layout.addWidget(QLabel("Предпросмотр"))
        layout.addWidget(self.preview_stack, 1)
        layout.addLayout(preview_buttons)
        layout.addLayout(buttons_row)
        return card

    def _connect_signals(self) -> None:
        self.game_combo.currentIndexChanged.connect(self._handle_game_changed)
        self.search_input.textChanged.connect(lambda _text: self._load_media())
        self.media_tree.itemSelectionChanged.connect(self._handle_media_selection_changed)
        self.browse_button.clicked.connect(self._browse_file)
        self.add_file_button.clicked.connect(self._import_media)
        self.save_binding_button.clicked.connect(self._save_binding)
        self.delete_button.clicked.connect(self._delete_media)
        self.preview_button.clicked.connect(self._preview_selected_media)

        self.import_role_combo.currentIndexChanged.connect(
            lambda _index: self._update_assignment_visibility(
                self.import_role_combo,
                self.import_round_combo,
                self.import_question_combo,
            )
        )
        self.edit_role_combo.currentIndexChanged.connect(
            lambda _index: self._update_assignment_visibility(
                self.edit_role_combo,
                self.edit_round_combo,
                self.edit_question_combo,
            )
        )

    def refresh(self) -> None:
        selected_game_id = self.game_combo.currentData()
        selected_media_id = self._selected_media_id()

        games = self.game_service.list_games()
        self.game_combo.blockSignals(True)
        self.game_combo.clear()
        for game in games:
            self.game_combo.addItem(game.title, game.id)
        self.game_combo.blockSignals(False)

        if selected_game_id is not None:
            index = self.game_combo.findData(selected_game_id)
            if index >= 0:
                self.game_combo.setCurrentIndex(index)

        self._refresh_targets()
        self._load_media()
        self._restore_media_selection(selected_media_id)
        self._update_selected_state()

    def set_current_game(self, game_id: int | None) -> None:
        if game_id is None:
            return
        index = self.game_combo.findData(game_id)
        if index >= 0:
            self.game_combo.setCurrentIndex(index)

    def get_selected_game(self) -> Game | None:
        game_id = self.game_combo.currentData()
        if game_id is None:
            return None
        return self.game_service.get_game(game_id)

    def _handle_game_changed(self) -> None:
        self._refresh_targets()
        self._load_media()
        self._clear_selected_editor()

    def _refresh_targets(self) -> None:
        game = self.get_selected_game()
        if game is None:
            self.cached_rounds = []
            self.cached_questions = []
        else:
            self.cached_rounds = self.round_service.list_rounds_by_game(game.id)
            self.cached_questions = []
            for round_item in self.cached_rounds:
                self.cached_questions.extend(
                    self.question_service.list_questions_by_round(round_item.id)
                )

        self._populate_round_combo(self.import_round_combo)
        self._populate_round_combo(self.edit_round_combo)
        self._populate_question_combo(self.import_question_combo)
        self._populate_question_combo(self.edit_question_combo)

    def _populate_round_combo(self, combo: QComboBox) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Не выбрано", None)
        for round_item in self.cached_rounds:
            combo.addItem(f"{round_item.order_index}. {round_item.title}", round_item.id)
        combo.blockSignals(False)

    def _populate_question_combo(self, combo: QComboBox) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Не выбрано", None)
        rounds_map = {round_item.id: round_item for round_item in self.cached_rounds}
        for question in self.cached_questions:
            round_item = rounds_map.get(question.round_id)
            round_label = round_item.title if round_item is not None else "Раунд"
            combo.addItem(
                f"{round_label} / {question.order_index}. {self._question_label(question)}",
                question.id,
            )
        combo.blockSignals(False)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите медиафайл",
            "",
            "Поддерживаемые файлы (*.png *.jpg *.jpeg *.webp *.mp4 *.webm *.mp3 *.wav *.ogg);;Все файлы (*)",
        )
        if path:
            self.import_path_input.setText(path)
            if not self.import_title_input.text().strip():
                self.import_title_input.setText(Path(path).stem)

    def _import_media(self) -> None:
        game = self.get_selected_game()
        if game is None:
            QMessageBox.warning(self, "Медиа", "Сначала создайте и выберите игру.")
            return

        try:
            created_media = self.media_service.import_media(
                game_id=game.id,
                title=self.import_title_input.text(),
                source_path=self.import_path_input.text(),
                usage_role=str(self.import_role_combo.currentData()),
                round_id=self.import_round_combo.currentData(),
                question_id=self.import_question_combo.currentData(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Медиа", str(error))
            return

        self.import_title_input.clear()
        self.import_path_input.clear()
        self.import_role_combo.setCurrentIndex(0)
        self.import_round_combo.setCurrentIndex(0)
        self.import_question_combo.setCurrentIndex(0)
        self.refresh()
        self._restore_media_selection(created_media.id)
        self.data_changed.emit()

    def _load_media(self) -> None:
        game = self.get_selected_game()
        query = self.search_input.text().strip().lower()

        self.media_tree.blockSignals(True)
        self.media_tree.clear()
        if game is not None:
            for media in self.media_service.list_media_by_game(game.id):
                target_label = self._target_label(media)
                haystack = f"{media.title} {media.original_filename} {target_label}".lower()
                if query and query not in haystack:
                    continue

                item = QTreeWidgetItem(
                    [
                        media.title,
                        self._format_type_label(media),
                        self.media_service.role_label(media.usage_role),
                        target_label,
                        media.original_filename or Path(media.file_path).name,
                    ]
                )
                item.setData(0, Qt.UserRole, media.id)
                item.setToolTip(0, media.file_path)
                item.setToolTip(3, target_label)
                item.setToolTip(4, media.file_path)
                self.media_tree.addTopLevelItem(item)
        self.media_tree.blockSignals(False)
        self.media_tree.resizeColumnToContents(1)
        self.media_tree.resizeColumnToContents(2)
        self.media_tree.resizeColumnToContents(3)

    def _handle_media_selection_changed(self) -> None:
        media = self._get_selected_media()
        if media is None:
            self._clear_selected_editor()
            return

        self.selected_title_input.setText(media.title)
        self._set_combo_to_value(self.edit_role_combo, media.usage_role)
        self._set_combo_to_value(self.edit_round_combo, media.round_id)
        self._set_combo_to_value(self.edit_question_combo, media.question_id)
        self._update_assignment_visibility(self.edit_role_combo, self.edit_round_combo, self.edit_question_combo)

        self.file_info_label.setText(
            f"Название: {media.title}\n\n"
            f"Тип: {self._format_type_label(media)}\n"
            f"Назначение: {self.media_service.role_label(media.usage_role)}\n"
            f"Привязка: {self._target_label(media)}\n"
            f"Оригинальный файл: {media.original_filename or Path(media.file_path).name}\n"
            f"Путь: {media.file_path}\n"
            f"Импортировано: {media.created_at}"
        )
        self._show_preview_placeholder(media)
        self._update_selected_state()

    def _save_binding(self) -> None:
        media = self._get_selected_media()
        if media is None:
            QMessageBox.warning(self, "Медиа", "Сначала выберите файл в библиотеке.")
            return

        try:
            updated_media = self.media_service.update_media_assignment(
                media_id=media.id,
                title=self.selected_title_input.text(),
                usage_role=str(self.edit_role_combo.currentData()),
                round_id=self.edit_round_combo.currentData(),
                question_id=self.edit_question_combo.currentData(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Медиа", str(error))
            return

        self.refresh()
        self._restore_media_selection(updated_media.id)
        self.data_changed.emit()

    def _delete_media(self) -> None:
        media = self._get_selected_media()
        if media is None:
            QMessageBox.warning(self, "Медиа", "Сначала выберите файл в библиотеке.")
            return

        answer = QMessageBox.question(
            self,
            "Удаление файла",
            f"Удалить файл «{media.title}» из медиабиблиотеки и с диска?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._stop_preview()
        try:
            self.media_service.delete_media(media.id)
        except ValueError as error:
            QMessageBox.warning(self, "Медиа", str(error))
            return

        self.refresh()
        self.data_changed.emit()

    def _preview_selected_media(self) -> None:
        media = self._get_selected_media()
        if media is None:
            QMessageBox.warning(self, "Медиа", "Сначала выберите файл.")
            return

        if media.media_type == "image":
            self._show_preview_placeholder(media)
            return

        if not QDesktopServices.openUrl(QUrl.fromLocalFile(media.file_path)):
            QMessageBox.warning(
                self,
                "Медиа",
                "Не удалось открыть файл системным приложением.",
            )

    def _show_preview_placeholder(self, media: MediaAsset) -> None:
        path = Path(media.file_path)
        if media.media_type == "image":
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                self.image_preview_label.setPixmap(QPixmap())
                self.image_preview_label.setText("Не удалось загрузить изображение.")
            else:
                self.image_preview_label.setText("")
                self.image_preview_label.setPixmap(
                    pixmap.scaled(
                        520,
                        320,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            self.preview_stack.setCurrentWidget(self.image_preview_label)
            return

        if media.media_type in {"video", "audio"}:
            self.preview_stack.setCurrentWidget(self.media_preview_label)
            return

        self.preview_stack.setCurrentWidget(self.empty_preview_label)

    def _clear_selected_editor(self) -> None:
        self.selected_title_input.clear()
        self.edit_role_combo.setCurrentIndex(0)
        self.edit_round_combo.setCurrentIndex(0)
        self.edit_question_combo.setCurrentIndex(0)
        self.file_info_label.setText("Выберите файл из библиотеки.")
        self.preview_stack.setCurrentWidget(self.empty_preview_label)
        self._update_selected_state()

    def _selected_media_id(self) -> int | None:
        item = self.media_tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.UserRole)

    def _get_selected_media(self) -> MediaAsset | None:
        media_id = self._selected_media_id()
        if media_id is None:
            return None
        return self.media_service.get_media(media_id)

    def _restore_media_selection(self, media_id: int | None) -> None:
        if media_id is None:
            return
        for index in range(self.media_tree.topLevelItemCount()):
            item = self.media_tree.topLevelItem(index)
            if item.data(0, Qt.UserRole) == media_id:
                self.media_tree.setCurrentItem(item)
                self._handle_media_selection_changed()
                break

    def _update_selected_state(self) -> None:
        has_media = self._get_selected_media() is not None
        self.selected_title_input.setEnabled(has_media)
        self.edit_role_combo.setEnabled(has_media)
        self.edit_round_combo.setEnabled(has_media)
        self.edit_question_combo.setEnabled(has_media)
        self.save_binding_button.setEnabled(has_media)
        self.delete_button.setEnabled(has_media)
        self.preview_button.setEnabled(has_media)

    def _build_role_combo(self) -> QComboBox:
        combo = QComboBox()
        role_order = [
            "library",
            "rules",
            "game_splash",
            "game_logo",
            "waiting_background",
            "pause",
            "sponsor",
            "background_music",
            "round",
            "question",
            "question_image",
            "question_video",
            "question_audio",
            "answer",
            "answer_image",
            "answer_video",
            "answer_audio",
            "option_a_image",
            "option_b_image",
            "option_c_image",
            "option_d_image",
        ]
        for role in role_order:
            combo.addItem(self.media_service.role_label(role), role)
        return combo

    def _update_assignment_visibility(
        self,
        role_combo: QComboBox,
        round_combo: QComboBox,
        question_combo: QComboBox,
    ) -> None:
        role = str(role_combo.currentData())
        show_round = role == "round"
        show_question = self.media_service.is_question_bound_role(role)

        round_combo.setVisible(show_round)
        question_combo.setVisible(show_question)

        form = self.import_form if role_combo is self.import_role_combo else self.edit_form
        round_label = form.labelForField(round_combo) if form is not None else None
        question_label = form.labelForField(question_combo) if form is not None else None
        if round_label is not None:
            round_label.setVisible(show_round)
        if question_label is not None:
            question_label.setVisible(show_question)

        if not show_round:
            round_combo.setCurrentIndex(0)
        if not show_question:
            question_combo.setCurrentIndex(0)

    def _target_label(self, media: MediaAsset) -> str:
        if media.usage_role == "library":
            return "Без привязки"
        if media.usage_role in {
            "rules",
            "game_splash",
            "game_logo",
            "waiting_background",
            "pause",
            "sponsor",
            "background_music",
        }:
            return "Уровень игры"
        if media.usage_role == "round":
            round_item = next((item for item in self.cached_rounds if item.id == media.round_id), None)
            return round_item.title if round_item is not None else "Раунд не найден"
        if self.media_service.is_question_bound_role(media.usage_role):
            question = next(
                (item for item in self.cached_questions if item.id == media.question_id),
                None,
            )
            if question is None:
                return "Вопрос не найден"
            suffix = {
                "question": "Основной блок вопроса",
                "question_image": "Картинка вопроса",
                "question_video": "Видео вопроса",
                "question_audio": "Аудио вопроса",
                "answer": "Основной блок ответа",
                "answer_image": "Картинка ответа",
                "answer_video": "Видео ответа",
                "answer_audio": "Аудио ответа",
                "option_a_image": "Картинка варианта A",
                "option_b_image": "Картинка варианта B",
                "option_c_image": "Картинка варианта C",
                "option_d_image": "Картинка варианта D",
            }.get(media.usage_role, self.media_service.role_label(media.usage_role))
            return f"{self._question_label(question)} / {suffix}"
        return "Без привязки"

    def _question_label(self, question: Question) -> str:
        base = " ".join(question.prompt.split())
        return base[:56] + ("..." if len(base) > 56 else "")

    def _format_type_label(self, media: MediaAsset) -> str:
        suffix = Path(media.original_filename or media.file_path).suffix.lower().lstrip(".")
        return f"{media.media_type.upper()} / {suffix}" if suffix else media.media_type.upper()

    def _set_combo_to_value(self, combo: QComboBox, value) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

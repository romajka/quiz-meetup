from __future__ import annotations

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
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
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from quiz_meetup.config import DEFAULT_QUESTION_TIMER_SECONDS
from quiz_meetup.models import Game, MediaAsset, Question, Round
from quiz_meetup.services.game_service import GameService
from quiz_meetup.services.media_service import MediaService
from quiz_meetup.services.question_service import QuestionService
from quiz_meetup.services.round_service import RoundService


class QuestionsPage(QWidget):
    data_changed = Signal()

    def __init__(
        self,
        game_service: GameService,
        round_service: RoundService,
        question_service: QuestionService,
        media_service: MediaService,
    ) -> None:
        super().__init__()
        self.game_service = game_service
        self.round_service = round_service
        self.question_service = question_service
        self.media_service = media_service

        self.current_question_id: int | None = None
        self._loading_state = False

        self._build_widgets()
        self._build_ui()
        self._connect_signals()
        self._update_question_type_ui()
        self._update_editor_state()

    def _build_widgets(self) -> None:
        self.round_combo = QComboBox()

        self.questions_list = QListWidget()
        self.questions_list.setSpacing(8)

        self.question_type_combo = QComboBox()
        self.question_type_combo.addItem("Открытый вопрос", "open")
        self.question_type_combo.addItem("ABCD вопрос", "abcd")

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Например: Вопрос 1")

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("Текст вопроса, который увидит ведущий и проектор.")
        self.prompt_input.setFixedHeight(120)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Комментарий для ведущего.")
        self.notes_input.setFixedHeight(90)

        self.answer_stack = QStackedWidget()
        self.open_answer_input = QLineEdit()
        self.open_answer_input.setPlaceholderText("Правильный ответ")
        self.abcd_answer_combo = QComboBox()
        self.abcd_answer_combo.addItem("A", "A")
        self.abcd_answer_combo.addItem("B", "B")
        self.abcd_answer_combo.addItem("C", "C")
        self.abcd_answer_combo.addItem("D", "D")
        self.answer_stack.addWidget(self.open_answer_input)
        self.answer_stack.addWidget(self.abcd_answer_combo)

        self.options_widget = QWidget()
        options_layout = QFormLayout(self.options_widget)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(8)
        self.option_a_input = QLineEdit()
        self.option_b_input = QLineEdit()
        self.option_c_input = QLineEdit()
        self.option_d_input = QLineEdit()
        self.option_a_input.setPlaceholderText("Вариант A или пусто для картинки")
        self.option_b_input.setPlaceholderText("Вариант B или пусто для картинки")
        self.option_c_input.setPlaceholderText("Вариант C или пусто для картинки")
        self.option_d_input.setPlaceholderText("Вариант D или пусто для картинки")
        options_layout.addRow("A", self.option_a_input)
        options_layout.addRow("B", self.option_b_input)
        options_layout.addRow("C", self.option_c_input)
        options_layout.addRow("D", self.option_d_input)

        self.points_input = QSpinBox()
        self.points_input.setRange(1, 100)
        self.points_input.setValue(1)

        self.timer_input = QSpinBox()
        self.timer_input.setRange(0, 900)
        self.timer_input.setValue(DEFAULT_QUESTION_TIMER_SECONDS)
        self.timer_input.setSpecialValueText("Без таймера")
        self.timer_input.setSuffix(" сек")

        self.new_question_button = QPushButton("Новый вопрос")
        self.new_question_button.setObjectName("SecondaryButton")
        self.move_up_button = QPushButton("Поднять выше")
        self.move_up_button.setObjectName("SecondaryButton")
        self.move_down_button = QPushButton("Опустить ниже")
        self.move_down_button.setObjectName("SecondaryButton")
        self.save_question_button = QPushButton("Создать вопрос")
        self.save_question_button.setObjectName("AccentButton")
        self.delete_question_button = QPushButton("Удалить вопрос")
        self.delete_question_button.setObjectName("DangerButton")

        self.question_media_label = QLabel(
            "Медиа вопроса пока не прикреплено. Можно добавить базовый файл здесь, а расширенные роли и ABCD-картинки задать на странице медиабиблиотеки."
        )
        self.question_media_label.setObjectName("DetailsLabel")
        self.question_media_label.setWordWrap(True)
        self.answer_media_label = QLabel(
            "Медиа ответа пока не прикреплено. Можно добавить базовый файл здесь, а расширенные роли и ABCD-картинки задать на странице медиабиблиотеки."
        )
        self.answer_media_label.setObjectName("DetailsLabel")
        self.answer_media_label.setWordWrap(True)

        self.add_question_media_button = QPushButton("Добавить или выбрать файл")
        self.add_question_media_button.setObjectName("SecondaryButton")
        self.open_question_media_button = QPushButton("Открыть файл вопроса")
        self.open_question_media_button.setObjectName("SecondaryButton")
        self.remove_question_media_button = QPushButton("Удалить файл вопроса")
        self.remove_question_media_button.setObjectName("DangerButton")

        self.add_answer_media_button = QPushButton("Добавить или выбрать файл")
        self.add_answer_media_button.setObjectName("SecondaryButton")
        self.open_answer_media_button = QPushButton("Открыть файл ответа")
        self.open_answer_media_button.setObjectName("SecondaryButton")
        self.remove_answer_media_button = QPushButton("Удалить файл ответа")
        self.remove_answer_media_button.setObjectName("DangerButton")

        self.details_label = QLabel("Сначала выберите раунд и вопрос.")
        self.details_label.setWordWrap(True)
        self.details_label.setObjectName("DetailsLabel")
        self.order_hint_label = QLabel("Порядок вопросов меняется кнопками сверху. Список идёт сверху вниз.")
        self.order_hint_label.setWordWrap(True)
        self.order_hint_label.setObjectName("PageHint")

        for button in (
            self.new_question_button,
            self.move_up_button,
            self.move_down_button,
            self.save_question_button,
            self.delete_question_button,
            self.add_question_media_button,
            self.open_question_media_button,
            self.remove_question_media_button,
            self.add_answer_media_button,
            self.open_answer_media_button,
            self.remove_answer_media_button,
        ):
            button.setMinimumHeight(46)

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QHBoxLayout(content)
        layout.setSpacing(16)

        left_card = QFrame()
        left_card.setObjectName("ContentCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(10)
        left_layout.addWidget(QLabel("Раунд"))
        left_layout.addWidget(self.round_combo)
        left_layout.addWidget(QLabel("Вопросы"))
        list_actions_layout = QHBoxLayout()
        list_actions_layout.setSpacing(10)
        list_actions_layout.addWidget(self.new_question_button)
        list_actions_layout.addWidget(self.move_up_button)
        list_actions_layout.addWidget(self.move_down_button)
        left_layout.addLayout(list_actions_layout)
        left_layout.addWidget(self.order_hint_label)
        left_layout.addWidget(self.questions_list, 1)
        self.questions_list.setMinimumHeight(420)

        right_card = QFrame()
        right_card.setObjectName("ContentCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)
        form_layout.addRow("Тип", self.question_type_combo)
        form_layout.addRow("Название вопроса", self.title_input)
        form_layout.addRow("Текст вопроса", self.prompt_input)
        form_layout.addRow("Правильный ответ", self.answer_stack)
        form_layout.addRow("Варианты ответа", self.options_widget)
        form_layout.addRow("Комментарий для ведущего", self.notes_input)
        form_layout.addRow("Очки", self.points_input)
        form_layout.addRow("Таймер", self.timer_input)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.addWidget(self.save_question_button)
        buttons_layout.addWidget(self.delete_question_button)

        media_layout = QHBoxLayout()
        media_layout.setSpacing(12)
        media_layout.addWidget(
            self._build_media_card(
                "Медиа вопроса",
                self.question_media_label,
                self.add_question_media_button,
                self.open_question_media_button,
                self.remove_question_media_button,
            ),
            1,
        )
        media_layout.addWidget(
            self._build_media_card(
                "Медиа ответа",
                self.answer_media_label,
                self.add_answer_media_button,
                self.open_answer_media_button,
                self.remove_answer_media_button,
            ),
            1,
        )

        right_layout.addLayout(form_layout)
        right_layout.addLayout(buttons_layout)
        right_layout.addLayout(media_layout)
        right_layout.addWidget(QLabel("Детали"))
        right_layout.addWidget(self.details_label)
        right_layout.addStretch(1)

        layout.addWidget(left_card, 2)
        layout.addWidget(right_card, 3)
        layout.addStretch(1)

        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area)

    def _build_media_card(
        self,
        title: str,
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

        caption = QLabel(title)
        caption.setObjectName("SectionCaption")
        layout.addWidget(caption)
        layout.addWidget(info_label)

        buttons = QGridLayout()
        buttons.setHorizontalSpacing(8)
        buttons.setVerticalSpacing(8)
        buttons.addWidget(add_button, 0, 0)
        buttons.addWidget(open_button, 0, 1)
        buttons.addWidget(remove_button, 1, 0, 1, 2)
        layout.addLayout(buttons)
        return card

    def _connect_signals(self) -> None:
        self.round_combo.currentIndexChanged.connect(self._load_questions)
        self.questions_list.itemSelectionChanged.connect(self._handle_question_selection_changed)
        self.question_type_combo.currentIndexChanged.connect(self._update_question_type_ui)
        self.new_question_button.clicked.connect(self.start_new_question)
        self.move_up_button.clicked.connect(self._move_question_up)
        self.move_down_button.clicked.connect(self._move_question_down)
        self.save_question_button.clicked.connect(self._save_question)
        self.delete_question_button.clicked.connect(self._delete_question)
        self.add_question_media_button.clicked.connect(
            lambda: self._attach_media_to_current_question("question")
        )
        self.open_question_media_button.clicked.connect(
            lambda: self._open_current_media("question")
        )
        self.remove_question_media_button.clicked.connect(
            lambda: self._remove_current_media("question")
        )
        self.add_answer_media_button.clicked.connect(
            lambda: self._attach_media_to_current_question("answer")
        )
        self.open_answer_media_button.clicked.connect(
            lambda: self._open_current_media("answer")
        )
        self.remove_answer_media_button.clicked.connect(
            lambda: self._remove_current_media("answer")
        )

    def refresh(self) -> None:
        selected_round_id = self.round_combo.currentData()
        selected_question_id = self.current_question_id

        games_map = {game.id: game.title for game in self.game_service.list_games()}
        rounds = self.round_service.list_all_rounds()

        self._loading_state = True
        self.round_combo.blockSignals(True)
        self.round_combo.clear()
        for round_item in rounds:
            game_title = games_map.get(round_item.game_id, "Без игры")
            self.round_combo.addItem(
                f"{game_title} / {round_item.order_index}. {round_item.title}",
                round_item.id,
            )
        self.round_combo.blockSignals(False)

        if selected_round_id is not None:
            index = self.round_combo.findData(selected_round_id)
            if index >= 0:
                self.round_combo.setCurrentIndex(index)

        self._loading_state = False
        self._load_questions()
        self._restore_question_selection(selected_question_id)
        self._update_editor_state()

    def get_selected_round(self) -> Round | None:
        round_id = self.round_combo.currentData()
        if round_id is None:
            return None
        return self.round_service.get_round(round_id)

    def get_selected_game(self) -> Game | None:
        round_item = self.get_selected_round()
        if round_item is None:
            return None
        return self.game_service.get_game(round_item.game_id)

    def set_current_game(self, game_id: int | None) -> None:
        if game_id is None:
            return

        rounds = self.round_service.list_rounds_by_game(game_id)
        if not rounds:
            self.round_combo.blockSignals(True)
            self.round_combo.clear()
            self.round_combo.blockSignals(False)
            self.questions_list.clear()
            self.current_question_id = None
            self._clear_form()
            self._update_media_state()
            self._update_details()
            self._update_editor_state()
            return

        target_round_id = rounds[0].id
        self.refresh()
        index = self.round_combo.findData(target_round_id)
        if index >= 0:
            self.round_combo.setCurrentIndex(index)

    def open_question(self, question_id: int | None) -> None:
        if question_id is None:
            return
        question = self.question_service.get_question(question_id)
        if question is None:
            return
        round_item = self.round_service.get_round(question.round_id)
        if round_item is None:
            return
        self.refresh()
        index = self.round_combo.findData(round_item.id)
        if index >= 0:
            self.round_combo.setCurrentIndex(index)
        self._restore_question_selection(question_id)

    def get_selected_question(self) -> Question | None:
        if self.current_question_id is None:
            return None
        return self.question_service.get_question(self.current_question_id)

    def start_new_question(self) -> None:
        round_item = self.get_selected_round()
        if round_item is None:
            QMessageBox.warning(self, "Вопросы", "Сначала выберите раунд.")
            return

        next_order = len(self.question_service.list_questions_by_round(round_item.id)) + 1
        try:
            question = self.question_service.create_question(
                round_id=round_item.id,
                title=f"Новый вопрос {next_order}",
                prompt=f"Новый вопрос {next_order}",
                question_type="open",
                notes="",
                answer="Ответ",
                option_a="",
                option_b="",
                option_c="",
                option_d="",
                points=1,
                order_index=None,
                timer_seconds=DEFAULT_QUESTION_TIMER_SECONDS,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Вопросы", str(error))
            return

        self.current_question_id = question.id
        self.refresh()
        self._restore_question_selection(question.id)
        self._update_media_state()
        self._update_details()
        self._update_editor_state()
        self.title_input.setFocus()
        self.title_input.selectAll()
        self.data_changed.emit()

    def _save_question(self) -> None:
        round_item = self.get_selected_round()
        if round_item is None:
            QMessageBox.warning(self, "Вопросы", "Сначала выберите раунд.")
            return

        question_type = str(self.question_type_combo.currentData())
        answer = (
            self.open_answer_input.text()
            if question_type == "open"
            else str(self.abcd_answer_combo.currentData())
        )

        try:
            if self.current_question_id is None:
                question = self.question_service.create_question(
                    round_id=round_item.id,
                    title=self.title_input.text(),
                    prompt=self.prompt_input.toPlainText(),
                    question_type=question_type,
                    notes=self.notes_input.toPlainText(),
                    answer=answer,
                    option_a=self.option_a_input.text(),
                    option_b=self.option_b_input.text(),
                    option_c=self.option_c_input.text(),
                    option_d=self.option_d_input.text(),
                    points=self.points_input.value(),
                    order_index=None,
                    timer_seconds=self.timer_input.value(),
                )
            else:
                question = self.question_service.update_question(
                    question_id=self.current_question_id,
                    title=self.title_input.text(),
                    prompt=self.prompt_input.toPlainText(),
                    question_type=question_type,
                    notes=self.notes_input.toPlainText(),
                    answer=answer,
                    option_a=self.option_a_input.text(),
                    option_b=self.option_b_input.text(),
                    option_c=self.option_c_input.text(),
                    option_d=self.option_d_input.text(),
                    points=self.points_input.value(),
                    timer_seconds=self.timer_input.value(),
                )
        except ValueError as error:
            QMessageBox.warning(self, "Вопросы", str(error))
            return

        self.current_question_id = question.id
        self.refresh()
        self._restore_question_selection(question.id)
        self.data_changed.emit()

    def _delete_question(self) -> None:
        question = self.get_selected_question()
        if question is None:
            QMessageBox.warning(self, "Вопросы", "Сначала выберите вопрос.")
            return

        answer = QMessageBox.question(
            self,
            "Удаление вопроса",
            f"Удалить вопрос «{question.title}»?",
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
        self.refresh()
        self.data_changed.emit()

    def _move_question_up(self) -> None:
        self._move_question(self.question_service.move_question_up)

    def _move_question_down(self) -> None:
        self._move_question(self.question_service.move_question_down)

    def _move_question(self, action) -> None:
        question = self.get_selected_question()
        if question is None:
            QMessageBox.warning(self, "Вопросы", "Сначала выберите вопрос.")
            return

        try:
            action(question.id)
        except ValueError as error:
            QMessageBox.warning(self, "Вопросы", str(error))
            return

        self.refresh()
        self._restore_question_selection(question.id)
        self.data_changed.emit()

    def _load_questions(self) -> None:
        round_item = self.get_selected_round()
        selected_question_id = self.current_question_id

        self._loading_state = True
        self.questions_list.blockSignals(True)
        self.questions_list.clear()
        if round_item is not None:
            for question in self.question_service.list_questions_by_round(round_item.id):
                item = QListWidgetItem(
                    f"{question.order_index}. {question.title}\n"
                    f"Очки: {question.points} | Таймер: {self._question_timer_label(question.timer_seconds)}"
                )
                item.setData(Qt.UserRole, question.id)
                self.questions_list.addItem(item)
        self.questions_list.blockSignals(False)
        self._loading_state = False

        if self.questions_list.count() == 0:
            self.current_question_id = None
            self._clear_form()
            self._update_media_state()
            self._update_details()
            self._update_editor_state()
            return

        self._restore_question_selection(selected_question_id)

    def _handle_question_selection_changed(self) -> None:
        if self._loading_state:
            return

        selected_items = self.questions_list.selectedItems()
        if not selected_items:
            self.current_question_id = None
            self._clear_form()
            self._update_media_state()
            self._update_details()
            self._update_editor_state()
            return

        item = selected_items[0]

        question_id = item.data(Qt.UserRole)
        question = self.question_service.get_question(question_id)
        if question is None:
            self.current_question_id = None
            self._clear_form()
            self._update_media_state()
            self._update_details()
            self._update_editor_state()
            return

        self.current_question_id = question.id
        self._loading_state = True
        self.title_input.setText(question.title)
        self.prompt_input.setPlainText(question.prompt)
        self.notes_input.setPlainText(question.notes)
        self.points_input.setValue(question.points)
        self.timer_input.setValue(question.timer_seconds)
        type_index = self.question_type_combo.findData(question.question_type)
        if type_index >= 0:
            self.question_type_combo.setCurrentIndex(type_index)
        self.open_answer_input.setText(question.answer if question.question_type == "open" else "")
        answer_index = self.abcd_answer_combo.findData(question.answer.upper())
        if answer_index >= 0:
            self.abcd_answer_combo.setCurrentIndex(answer_index)
        self.option_a_input.setText(question.option_a)
        self.option_b_input.setText(question.option_b)
        self.option_c_input.setText(question.option_c)
        self.option_d_input.setText(question.option_d)
        self._loading_state = False

        self._update_question_type_ui()
        self._update_media_state()
        self._update_details()
        self._update_editor_state()

    def _restore_question_selection(self, question_id: int | None) -> None:
        if self.questions_list.count() == 0:
            return

        target_row = 0
        if question_id is not None:
            for index in range(self.questions_list.count()):
                if self.questions_list.item(index).data(Qt.UserRole) == question_id:
                    target_row = index
                    break
        self.questions_list.setCurrentRow(target_row)
        self._handle_question_selection_changed()

    def _update_question_type_ui(self) -> None:
        is_abcd = self.question_type_combo.currentData() == "abcd"
        self.answer_stack.setCurrentIndex(1 if is_abcd else 0)
        self.options_widget.setVisible(is_abcd)

    def _update_editor_state(self) -> None:
        has_round = self.get_selected_round() is not None
        has_question = self.current_question_id is not None
        question_media = self._get_current_media("question")
        answer_media = self._get_current_media("answer")

        for widget in (
            self.question_type_combo,
            self.title_input,
            self.prompt_input,
            self.notes_input,
            self.points_input,
            self.timer_input,
            self.open_answer_input,
            self.abcd_answer_combo,
            self.options_widget,
        ):
            widget.setEnabled(has_round)

        self.new_question_button.setEnabled(has_round)
        self.move_up_button.setEnabled(has_question)
        self.move_down_button.setEnabled(has_question)
        self.save_question_button.setEnabled(has_round)
        self.delete_question_button.setEnabled(has_question)
        self.add_question_media_button.setEnabled(has_question)
        self.add_answer_media_button.setEnabled(has_question)
        self.open_question_media_button.setEnabled(question_media is not None)
        self.remove_question_media_button.setEnabled(question_media is not None)
        self.open_answer_media_button.setEnabled(answer_media is not None)
        self.remove_answer_media_button.setEnabled(answer_media is not None)
        self.save_question_button.setText("Сохранить вопрос" if has_question else "Создать вопрос")

    def _update_details(self) -> None:
        question = self.get_selected_question()
        if question is None:
            self.details_label.setText("Выберите вопрос из списка или создайте новый.")
            return

        answer = question.answer or "Ответ пока не заполнен."
        self.details_label.setText(
            f"Название: {question.title}\n\n"
            f"Текст: {question.prompt}\n\n"
            f"Тип: {'Открытый' if question.question_type == 'open' else 'ABCD'}\n\n"
            f"Ответ: {answer}\n\n"
            f"Очки: {question.points}\n"
            f"Порядок: {question.order_index}\n"
            f"Таймер: {self._question_timer_label(question.timer_seconds)}"
        )

    def _clear_form(self) -> None:
        self._loading_state = True
        self.title_input.clear()
        self.prompt_input.clear()
        self.notes_input.clear()
        self.question_type_combo.setCurrentIndex(0)
        self.open_answer_input.clear()
        self.abcd_answer_combo.setCurrentIndex(0)
        self.option_a_input.clear()
        self.option_b_input.clear()
        self.option_c_input.clear()
        self.option_d_input.clear()
        self.points_input.setValue(1)
        self.timer_input.setValue(DEFAULT_QUESTION_TIMER_SECONDS)
        self._loading_state = False
        self._update_question_type_ui()

    def _get_current_media(self, usage_role: str) -> MediaAsset | None:
        round_item = self.get_selected_round()
        question = self.get_selected_question()
        if round_item is None or question is None:
            return None
        return self.media_service.find_media_for_question(
            game_id=round_item.game_id,
            question_id=question.id,
            usage_role=usage_role,
        )

    def _update_media_state(self) -> None:
        self.question_media_label.setText(
            self._media_label_text(
                self._get_current_media("question"),
                "Медиа вопроса пока не прикреплено. Можно добавить изображение, видео или аудио.",
            )
        )
        self.answer_media_label.setText(
            self._media_label_text(
                self._get_current_media("answer"),
                "Медиа ответа пока не прикреплено. Можно добавить изображение, видео или аудио.",
            )
        )

    def _media_label_text(self, media: MediaAsset | None, empty_text: str) -> str:
        if media is None:
            return empty_text
        return (
            f"Файл: {media.title}\n"
            f"Тип: {self.media_service.role_label(media.usage_role)} / {media.media_type}\n"
            f"Путь: {media.file_path}"
        )

    def _attach_media_to_current_question(self, usage_role: str) -> None:
        round_item = self.get_selected_round()
        question = self.get_selected_question()
        if round_item is None or question is None:
            QMessageBox.warning(self, "Медиа", "Сначала выберите или сохраните вопрос.")
            return

        source_mode = self._prompt_media_source()
        if source_mode is None:
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
                    game_id=round_item.game_id,
                    question_id=question.id,
                    usage_role=usage_role,
                    source_path=source_path,
                    title=f"{'Вопрос' if usage_role == 'question' else 'Ответ'} — {question.title}",
                )
            except ValueError as error:
                QMessageBox.warning(self, "Медиа", str(error))
                return
        else:
            media = self._choose_existing_media(round_item.game_id, usage_role)
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

        self._update_media_state()
        self._update_editor_state()
        self.data_changed.emit()

    def _open_current_media(self, usage_role: str) -> None:
        media = self._get_current_media(usage_role)
        if media is None:
            QMessageBox.warning(self, "Медиа", "Для этого блока файл пока не выбран.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(media.file_path)):
            QMessageBox.warning(self, "Медиа", "Не удалось открыть файл системным приложением.")

    def _remove_current_media(self, usage_role: str) -> None:
        round_item = self.get_selected_round()
        question = self.get_selected_question()
        media = self._get_current_media(usage_role)
        if round_item is None or question is None or media is None:
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
            game_id=round_item.game_id,
            question_id=question.id,
            usage_role=usage_role,
        )
        self._update_media_state()
        self._update_editor_state()
        self.data_changed.emit()

    def _question_timer_label(self, timer_seconds: int) -> str:
        if timer_seconds <= 0:
            return "без таймера"
        return f"{timer_seconds} сек"

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

    def _choose_existing_media(self, game_id: int, usage_role: str) -> MediaAsset | None:
        media_assets = self.media_service.list_media_by_game(game_id)
        if not media_assets:
            QMessageBox.warning(self, "Медиа", "Для этой игры пока нет загруженных файлов.")
            return None

        label_map: dict[str, MediaAsset] = {}
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

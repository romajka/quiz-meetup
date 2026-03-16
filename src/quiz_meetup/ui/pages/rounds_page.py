from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from quiz_meetup.config import DEFAULT_ROUND_TIMER_SECONDS
from quiz_meetup.models import Game, Round
from quiz_meetup.services.game_service import GameService
from quiz_meetup.services.round_service import RoundService


class RoundsPage(QWidget):
    data_changed = Signal()

    def __init__(self, game_service: GameService, round_service: RoundService) -> None:
        super().__init__()
        self.game_service = game_service
        self.round_service = round_service

        self.current_round_id: int | None = None
        self._loading_state = False

        self._build_widgets()
        self._build_ui()
        self._connect_signals()
        self._update_editor_state()

    def _build_widgets(self) -> None:
        self.game_combo = QComboBox()

        self.rounds_list = QListWidget()
        self.rounds_list.setSpacing(8)

        self.title_input = QTextEdit()
        self.title_input.setFixedHeight(56)
        self.title_input.setPlaceholderText("Например: Разминка")

        self.order_input = QSpinBox()
        self.order_input.setMinimum(1)
        self.order_input.setMaximum(999)
        self.order_input.setValue(1)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Заметки для ведущего по этому раунду.")
        self.notes_input.setFixedHeight(120)

        self.new_round_button = QPushButton("Новый раунд")
        self.new_round_button.setObjectName("SecondaryButton")
        self.save_round_button = QPushButton("Создать раунд")
        self.save_round_button.setObjectName("AccentButton")
        self.delete_round_button = QPushButton("Удалить раунд")
        self.delete_round_button.setObjectName("DangerButton")
        self.move_up_button = QPushButton("Выше")
        self.move_up_button.setObjectName("SecondaryButton")
        self.move_down_button = QPushButton("Ниже")
        self.move_down_button.setObjectName("SecondaryButton")

        self.details_label = QLabel("Сначала выберите игру.")
        self.details_label.setWordWrap(True)
        self.details_label.setObjectName("DetailsLabel")

        for button in (
            self.new_round_button,
            self.save_round_button,
            self.delete_round_button,
            self.move_up_button,
            self.move_down_button,
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
        left_layout.addWidget(QLabel("Игра"))
        left_layout.addWidget(self.game_combo)
        left_layout.addWidget(QLabel("Раунды"))
        top_actions_layout = QHBoxLayout()
        top_actions_layout.setSpacing(10)
        top_actions_layout.addWidget(self.new_round_button)
        top_actions_layout.addWidget(self.move_up_button)
        top_actions_layout.addWidget(self.move_down_button)
        left_layout.addLayout(top_actions_layout)
        left_layout.addWidget(self.rounds_list, 1)
        self.rounds_list.setMinimumHeight(380)

        right_card = QFrame()
        right_card.setObjectName("ContentCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(10)
        right_layout.addWidget(QLabel("Название раунда"))
        right_layout.addWidget(self.title_input)
        right_layout.addWidget(QLabel("Порядок"))
        right_layout.addWidget(self.order_input)
        right_layout.addWidget(QLabel("Заметки"))
        right_layout.addWidget(self.notes_input)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        action_layout.addWidget(self.save_round_button)
        action_layout.addWidget(self.delete_round_button)

        right_layout.addLayout(action_layout)
        right_layout.addSpacing(12)
        right_layout.addWidget(QLabel("Детали"))
        right_layout.addWidget(self.details_label)
        right_layout.addStretch(1)

        layout.addWidget(left_card, 2)
        layout.addWidget(right_card, 3)
        layout.addStretch(1)

        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area)

    def _connect_signals(self) -> None:
        self.game_combo.currentIndexChanged.connect(self._load_rounds)
        self.rounds_list.itemSelectionChanged.connect(self._handle_round_selection_changed)
        self.new_round_button.clicked.connect(self.start_new_round)
        self.save_round_button.clicked.connect(self._save_round)
        self.delete_round_button.clicked.connect(self._delete_round)
        self.move_up_button.clicked.connect(self._move_round_up)
        self.move_down_button.clicked.connect(self._move_round_down)

    def refresh(self) -> None:
        current_game_id = self.game_combo.currentData()
        current_round_id = self.current_round_id
        games = self.game_service.list_games()

        self._loading_state = True
        self.game_combo.blockSignals(True)
        self.game_combo.clear()
        for game in games:
            self.game_combo.addItem(game.title, game.id)
        self.game_combo.blockSignals(False)

        if current_game_id is not None:
            index = self.game_combo.findData(current_game_id)
            if index >= 0:
                self.game_combo.setCurrentIndex(index)

        self._loading_state = False
        self._load_rounds()
        self._restore_round_selection(current_round_id)
        self._update_editor_state()

    def get_selected_game(self) -> Game | None:
        game_id = self.game_combo.currentData()
        if game_id is None:
            return None
        return self.game_service.get_game(game_id)

    def set_current_game(self, game_id: int | None) -> None:
        if game_id is None:
            return
        index = self.game_combo.findData(game_id)
        if index >= 0:
            self.game_combo.setCurrentIndex(index)

    def get_selected_round(self) -> Round | None:
        if self.current_round_id is None:
            return None
        return self.round_service.get_round(self.current_round_id)

    def start_new_round(self) -> None:
        game = self.get_selected_game()
        if game is None:
            QMessageBox.warning(self, "Раунды", "Сначала создайте и выберите игру.")
            return

        next_order = self._next_order_for_current_game()
        try:
            round_item = self.round_service.create_round(
                game_id=game.id,
                title=f"Новый раунд {next_order}",
                order_index=next_order,
                timer_seconds=DEFAULT_ROUND_TIMER_SECONDS,
                notes="",
            )
        except ValueError as error:
            QMessageBox.warning(self, "Раунды", str(error))
            return

        self.current_round_id = round_item.id
        self.refresh()
        self._restore_round_selection(round_item.id)
        self.details_label.setText("Новый раунд создан. Теперь отредактируйте его справа.")
        self._update_editor_state()
        self.title_input.setFocus()
        self.title_input.selectAll()
        self.data_changed.emit()

    def _save_round(self) -> None:
        game = self.get_selected_game()
        if game is None:
            QMessageBox.warning(self, "Раунды", "Сначала выберите игру.")
            return

        try:
            if self.current_round_id is None:
                round_item = self.round_service.create_round(
                    game_id=game.id,
                    title=self.title_input.toPlainText(),
                    order_index=self.order_input.value(),
                    timer_seconds=DEFAULT_ROUND_TIMER_SECONDS,
                    notes=self.notes_input.toPlainText(),
                )
            else:
                current_round = self.get_selected_round()
                round_item = self.round_service.update_round(
                    round_id=self.current_round_id,
                    title=self.title_input.toPlainText(),
                    timer_seconds=current_round.timer_seconds if current_round is not None else DEFAULT_ROUND_TIMER_SECONDS,
                    notes=self.notes_input.toPlainText(),
                )
        except ValueError as error:
            QMessageBox.warning(self, "Раунды", str(error))
            return

        self.current_round_id = round_item.id
        self.refresh()
        self._restore_round_selection(round_item.id)
        self.data_changed.emit()

    def _delete_round(self) -> None:
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
        self.refresh()
        self.data_changed.emit()

    def _move_round_up(self) -> None:
        self._move_round(self.round_service.move_round_up)

    def _move_round_down(self) -> None:
        self._move_round(self.round_service.move_round_down)

    def _move_round(self, action) -> None:
        round_item = self.get_selected_round()
        if round_item is None:
            QMessageBox.warning(self, "Раунды", "Сначала выберите раунд.")
            return

        try:
            action(round_item.id)
        except ValueError as error:
            QMessageBox.warning(self, "Раунды", str(error))
            return

        self.refresh()
        self._restore_round_selection(round_item.id)
        self.data_changed.emit()

    def _load_rounds(self) -> None:
        game = self.get_selected_game()
        selected_round_id = self.current_round_id

        self._loading_state = True
        self.rounds_list.blockSignals(True)
        self.rounds_list.clear()
        if game is not None:
            for round_item in self.round_service.list_rounds_by_game(game.id):
                item = QListWidgetItem(
                    f"{round_item.order_index}. {round_item.title}"
                )
                item.setData(Qt.UserRole, round_item.id)
                self.rounds_list.addItem(item)
        self.rounds_list.blockSignals(False)
        self._loading_state = False

        if self.rounds_list.count() == 0:
            self.current_round_id = None
            self._clear_form()
            self.order_input.setValue(self._next_order_for_current_game())
            self.details_label.setText("Для этой игры пока нет раундов. Создайте первый.")
            self._update_editor_state()
            return

        self._restore_round_selection(selected_round_id)

    def _handle_round_selection_changed(self) -> None:
        if self._loading_state:
            return

        selected_items = self.rounds_list.selectedItems()
        if not selected_items:
            self.current_round_id = None
            self._clear_form()
            self.order_input.setValue(self._next_order_for_current_game())
            self.details_label.setText("Выберите раунд из списка или создайте новый.")
            self._update_editor_state()
            return

        item = selected_items[0]

        round_id = item.data(Qt.UserRole)
        round_item = self.round_service.get_round(round_id)
        if round_item is None:
            self.current_round_id = None
            self._clear_form()
            self._update_editor_state()
            return

        self.current_round_id = round_item.id
        self._loading_state = True
        self.title_input.setPlainText(round_item.title)
        self.order_input.setValue(round_item.order_index)
        self.notes_input.setPlainText(round_item.notes)
        self._loading_state = False
        self._update_details()
        self._update_editor_state()

    def _update_details(self) -> None:
        round_item = self.get_selected_round()
        if round_item is None:
            self.details_label.setText("Пока нет выбранного раунда.")
            return

        notes = round_item.notes or "Заметки не заполнены."
        self.details_label.setText(
            f"Название: {round_item.title}\n\n"
            f"Порядок: {round_item.order_index}\n"
            f"Режим игры: Презентация / Команды\n\n"
            f"Заметки: {notes}"
        )

    def _restore_round_selection(self, round_id: int | None) -> None:
        if self.rounds_list.count() == 0:
            return

        target_row = 0
        if round_id is not None:
            for index in range(self.rounds_list.count()):
                if self.rounds_list.item(index).data(Qt.UserRole) == round_id:
                    target_row = index
                    break
        self.rounds_list.setCurrentRow(target_row)
        self._handle_round_selection_changed()

    def _update_editor_state(self) -> None:
        has_game = self.get_selected_game() is not None
        has_round = self.current_round_id is not None

        for widget in (self.title_input, self.order_input, self.notes_input):
            widget.setEnabled(has_game)

        self.new_round_button.setEnabled(has_game)
        self.save_round_button.setEnabled(has_game)
        self.delete_round_button.setEnabled(has_round)
        self.move_up_button.setEnabled(has_round)
        self.move_down_button.setEnabled(has_round)
        self.order_input.setEnabled(has_game and not has_round)
        self.save_round_button.setText("Сохранить раунд" if has_round else "Создать раунд")

    def _clear_form(self) -> None:
        self._loading_state = True
        self.title_input.clear()
        self.order_input.setValue(1)
        self.notes_input.clear()
        self._loading_state = False

    def _next_order_for_current_game(self) -> int:
        game = self.get_selected_game()
        if game is None:
            return 1
        rounds = self.round_service.list_rounds_by_game(game.id)
        return len(rounds) + 1

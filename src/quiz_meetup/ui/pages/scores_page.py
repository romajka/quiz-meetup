from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QComboBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from quiz_meetup.models import Game, ScoreboardRow
from quiz_meetup.services.game_service import GameService
from quiz_meetup.services.question_service import QuestionService
from quiz_meetup.services.round_service import RoundService
from quiz_meetup.services.score_service import ScoreService
from quiz_meetup.services.team_service import TeamService


class ScoreValueDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 0:
            return None
        editor = QSpinBox(parent)
        editor.setRange(0, 9999)
        editor.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        editor.setFrame(False)
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        editor.editingFinished.connect(self._commit_editor)
        return editor

    def setEditorData(self, editor, index) -> None:
        try:
            value = int(index.data(Qt.ItemDataRole.EditRole) or 0)
        except (TypeError, ValueError):
            value = 0
        editor.setValue(value)
        editor.selectAll()

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, str(editor.value()), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index) -> None:
        editor.setGeometry(option.rect)

    def _commit_editor(self) -> None:
        editor = self.sender()
        if editor is None:
            return
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.EndEditHint.NoHint)


class ScoresPage(QWidget):
    data_changed = Signal()
    CELL_KIND_ROLE = Qt.UserRole + 1

    def __init__(
        self,
        game_service: GameService,
        round_service: RoundService,
        question_service: QuestionService,
        score_service: ScoreService,
        team_service: TeamService,
    ) -> None:
        super().__init__()
        self.game_service = game_service
        self.round_service = round_service
        self.question_service = question_service
        self.score_service = score_service
        self.team_service = team_service

        self.rounds_by_id: dict[int, object] = {}
        self.scoreboard_rows: list[ScoreboardRow] = []
        self.visible_round_ids: list[int] = []
        self._loading_score_table = False
        self.current_session_id: int | None = None
        self.current_session_game_id: int | None = None

        self.game_combo = QComboBox()
        self.game_combo.currentIndexChanged.connect(self._handle_game_changed)

        self.round_combo = QComboBox()
        self.round_combo.currentIndexChanged.connect(self._load_questions)

        self.question_combo = QComboBox()
        self.question_combo.currentIndexChanged.connect(self._update_question_defaults)

        self.score_table = QTableWidget(0, 0)
        self.score_table.verticalHeader().setVisible(False)
        self.score_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.score_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.score_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.score_table.setWordWrap(False)
        self.score_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.score_table.setEditTriggers(
            QAbstractItemView.EditTrigger.CurrentChanged
            | QAbstractItemView.EditTrigger.AnyKeyPressed
            | QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.score_table.setItemDelegate(ScoreValueDelegate(self.score_table))
        self.score_table.itemSelectionChanged.connect(self._update_details)

        self.question_points_input = QSpinBox()
        self.question_points_input.setRange(0, 999)

        self.team_name_input = QLineEdit()
        self.team_name_input.setPlaceholderText("Например: Команда Север")

        self.round_adjustment_input = QSpinBox()
        self.round_adjustment_input.setRange(-999, 999)

        self.total_score_input = QSpinBox()
        self.total_score_input.setRange(0, 9999)

        self.selected_team_label = QLabel("Выбранная команда: не выбрана")
        self.selected_team_label.setObjectName("SectionCaption")

        self.table_hint_label = QLabel(
            "Суммы по раундам и итог можно менять прямо в ячейках таблицы. Место команды пересчитывается автоматически."
        )
        self.table_hint_label.setWordWrap(True)
        self.table_hint_label.setObjectName("DetailsLabel")

        self.details_label = QLabel("Выберите игру, команду и вопрос для начисления очков.")
        self.details_label.setWordWrap(True)
        self.details_label.setObjectName("DetailsLabel")

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setSpacing(16)

        left_card = QFrame()
        left_card.setObjectName("ContentCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(10)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        game_layout = QVBoxLayout()
        game_layout.addWidget(QLabel("Игра"))
        game_layout.addWidget(self.game_combo)

        round_layout = QVBoxLayout()
        round_layout.addWidget(QLabel("Раунд"))
        round_layout.addWidget(self.round_combo)

        question_layout = QVBoxLayout()
        question_layout.addWidget(QLabel("Вопрос"))
        question_layout.addWidget(self.question_combo)

        filter_layout.addLayout(game_layout, 2)
        filter_layout.addLayout(round_layout, 2)
        filter_layout.addLayout(question_layout, 3)

        left_layout.addLayout(filter_layout)
        left_layout.addWidget(QLabel("Итоговая таблица"))
        left_layout.addWidget(self.table_hint_label)
        left_layout.addWidget(self.score_table, 1)

        right_card = QFrame()
        right_card.setObjectName("ContentCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(10)

        question_form = QFormLayout()
        question_form.setSpacing(10)
        question_form.addRow("Команда", self.team_name_input)
        question_form.addRow("Очки за вопрос", self.question_points_input)

        round_form = QFormLayout()
        round_form.setSpacing(10)
        round_form.addRow("Ручная корректировка раунда", self.round_adjustment_input)
        round_form.addRow("Ручной итог команды", self.total_score_input)

        self.award_question_button = QPushButton("Засчитать максимум вопроса")
        self.award_question_button.setObjectName("AccentButton")
        self.add_team_button = QPushButton("Добавить команду")
        self.add_team_button.setObjectName("AccentButton")
        self.rename_team_button = QPushButton("Сохранить название команды")
        self.rename_team_button.setObjectName("SecondaryButton")
        self.delete_team_button = QPushButton("Удалить команду")
        self.delete_team_button.setObjectName("DangerButton")
        self.set_question_button = QPushButton("Сохранить очки вопроса")
        self.set_round_adjustment_button = QPushButton("Сохранить корректировку раунда")
        self.set_total_button = QPushButton("Сохранить ручной итог")
        self.reset_team_button = QPushButton("Сбросить очки команды")
        self.reset_team_button.setObjectName("SecondaryButton")
        self.reset_game_button = QPushButton("Сбросить все результаты")
        self.reset_game_button.setObjectName("DangerButton")

        right_layout.addWidget(self.selected_team_label)
        right_layout.addWidget(self.add_team_button)
        right_layout.addWidget(self.rename_team_button)
        right_layout.addWidget(self.delete_team_button)
        right_layout.addWidget(self.award_question_button)
        right_layout.addLayout(question_form)
        right_layout.addWidget(self.set_question_button)
        right_layout.addSpacing(10)
        right_layout.addLayout(round_form)
        right_layout.addWidget(self.set_round_adjustment_button)
        right_layout.addWidget(self.set_total_button)
        right_layout.addSpacing(10)
        right_layout.addWidget(self.reset_team_button)
        right_layout.addWidget(self.reset_game_button)
        right_layout.addSpacing(16)
        right_layout.addWidget(QLabel("Детали"))
        right_layout.addWidget(self.details_label)
        right_layout.addStretch(1)

        for button in (
            self.award_question_button,
            self.add_team_button,
            self.rename_team_button,
            self.delete_team_button,
            self.set_question_button,
            self.set_round_adjustment_button,
            self.set_total_button,
            self.reset_team_button,
            self.reset_game_button,
        ):
            button.setMinimumHeight(46)

        layout.addWidget(left_card, 4)
        layout.addWidget(right_card, 2)

    def _connect_signals(self) -> None:
        self.add_team_button.clicked.connect(self._create_team)
        self.rename_team_button.clicked.connect(self._rename_team)
        self.delete_team_button.clicked.connect(self._delete_team)
        self.award_question_button.clicked.connect(self._award_selected_question)
        self.set_question_button.clicked.connect(self._set_question_points)
        self.set_round_adjustment_button.clicked.connect(self._set_round_adjustment)
        self.set_total_button.clicked.connect(self._set_total_score)
        self.reset_team_button.clicked.connect(self._reset_team_scores)
        self.reset_game_button.clicked.connect(self._reset_game_scores)
        self.score_table.itemChanged.connect(self._handle_score_item_changed)

    def refresh(self) -> None:
        selected_game_id = self.game_combo.currentData()
        selected_team_id = self._selected_team_id()
        selected_round_id = self.round_combo.currentData()
        selected_question_id = self.question_combo.currentData()
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

        self._load_rounds(preferred_round_id=selected_round_id)
        self._load_questions(preferred_question_id=selected_question_id)
        self._load_scores(preferred_team_id=selected_team_id)

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

    def set_current_session(self, session_id: int | None, game_id: int | None = None) -> None:
        self.current_session_id = session_id
        self.current_session_game_id = game_id
        if game_id is not None:
            self.set_current_game(game_id)
        self._load_rounds(preferred_round_id=self.round_combo.currentData())
        self._load_questions(preferred_question_id=self.question_combo.currentData())
        self._load_scores(preferred_team_id=self._selected_team_id())

    def _handle_game_changed(self) -> None:
        game_id = self.game_combo.currentData()
        if (
            self.current_session_id is not None
            and self.current_session_game_id is not None
            and game_id != self.current_session_game_id
        ):
            self.current_session_id = None
            self.current_session_game_id = None
        self._load_rounds()
        self._load_questions()
        self._load_scores()

    def _load_rounds(self, preferred_round_id: int | None = None) -> None:
        game = self.get_selected_game()
        rounds = self.round_service.list_rounds_by_game(game.id) if game is not None else []
        self.rounds_by_id = {round_item.id: round_item for round_item in rounds}

        self.round_combo.blockSignals(True)
        self.round_combo.clear()
        for round_item in rounds:
            self.round_combo.addItem(f"{round_item.order_index}. {round_item.title}", round_item.id)
        self.round_combo.blockSignals(False)

        if preferred_round_id is not None:
            index = self.round_combo.findData(preferred_round_id)
            if index >= 0:
                self.round_combo.setCurrentIndex(index)

    def _load_questions(self, preferred_question_id: int | None = None) -> None:
        round_id = self.round_combo.currentData()
        questions = self.question_service.list_questions_by_round(round_id) if round_id is not None else []

        self.question_combo.blockSignals(True)
        self.question_combo.clear()
        for question in questions:
            self.question_combo.addItem(
                f"{question.order_index}. {question.title} ({question.points} очк.)",
                question.id,
            )
        self.question_combo.blockSignals(False)

        if preferred_question_id is not None:
            index = self.question_combo.findData(preferred_question_id)
            if index >= 0:
                self.question_combo.setCurrentIndex(index)

        self._update_question_defaults()

    def _load_scores(self, preferred_team_id: int | None = None) -> None:
        game = self.get_selected_game()
        rounds = self.round_service.list_rounds_by_game(game.id) if game is not None else []
        self.visible_round_ids = [round_item.id for round_item in rounds]
        if game is None:
            self.scoreboard_rows = []
        elif self.current_session_id is not None:
            self.scoreboard_rows = self.score_service.get_scoreboard_rows_for_session(
                self.current_session_id,
                game.id,
            )
        else:
            self.scoreboard_rows = self.score_service.get_scoreboard_rows(game.id)

        headers = ["Место", "Команда"] + [round_item.title for round_item in rounds] + ["Итог"]
        self._loading_score_table = True
        self.score_table.blockSignals(True)
        self.score_table.clear()
        self.score_table.setColumnCount(len(headers))
        self.score_table.setHorizontalHeaderLabels(headers)
        header = self.score_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.score_table.setColumnWidth(1, 320)
        for column in range(2, len(headers) - 1):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
            self.score_table.setColumnWidth(column, 170)
        if headers:
            header.setSectionResizeMode(len(headers) - 1, QHeaderView.Interactive)
            self.score_table.setColumnWidth(len(headers) - 1, 120)

        self.score_table.setRowCount(len(self.scoreboard_rows))
        for row_index, row in enumerate(self.scoreboard_rows):
            place_item = QTableWidgetItem(str(row_index + 1))
            place_item.setTextAlignment(Qt.AlignCenter)
            place_item.setData(Qt.UserRole, row.team_id)
            place_item.setFlags(place_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.score_table.setItem(row_index, 0, place_item)

            team_item = QTableWidgetItem(row.team_name)
            team_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            team_item.setToolTip(row.team_name)
            team_item.setData(Qt.UserRole, row.team_id)
            team_item.setFlags(team_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.score_table.setItem(row_index, 1, team_item)
            for column_index, round_item in enumerate(rounds, start=2):
                round_score_item = QTableWidgetItem(str(row.round_scores.get(round_item.id, 0)))
                round_score_item.setTextAlignment(Qt.AlignCenter)
                round_score_item.setData(Qt.UserRole, row.team_id)
                round_score_item.setData(self.CELL_KIND_ROLE, ("round", round_item.id))
                self.score_table.setItem(row_index, column_index, round_score_item)
            total_item = QTableWidgetItem(str(row.total_score))
            total_item.setTextAlignment(Qt.AlignCenter)
            total_item.setData(Qt.UserRole, row.team_id)
            total_item.setData(self.CELL_KIND_ROLE, ("total", None))
            self.score_table.setItem(row_index, len(headers) - 1, total_item)

        self.score_table.blockSignals(False)
        self._loading_score_table = False

        if self.scoreboard_rows:
            self._restore_team_selection(preferred_team_id)
        else:
            self.selected_team_label.setText("Выбранная команда: не выбрана")
            self.details_label.setText("Для выбранной игры пока нет команд.")

    def _award_selected_question(self) -> None:
        team_id = self._selected_team_id()
        question_id = self.question_combo.currentData()
        if team_id is None or question_id is None:
            QMessageBox.warning(self, "Очки", "Сначала выберите команду и вопрос.")
            return
        try:
            self.score_service.award_question_score(team_id, question_id)
        except ValueError as error:
            QMessageBox.warning(self, "Очки", str(error))
            return
        self._reload_after_score_change(team_id)

    def _create_team(self) -> None:
        game = self.get_selected_game()
        if game is None:
            QMessageBox.warning(self, "Команды", "Сначала выберите игру.")
            return

        try:
            created_team = self.team_service.create_team(
                game_id=game.id,
                name=self.team_name_input.text(),
                session_id=self.current_session_id,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Команды", str(error))
            return

        self.team_name_input.clear()
        self.refresh()
        self._restore_team_selection(created_team.id)
        self.data_changed.emit()

    def _set_question_points(self) -> None:
        team_id = self._selected_team_id()
        question_id = self.question_combo.currentData()
        if team_id is None or question_id is None:
            QMessageBox.warning(self, "Очки", "Сначала выберите команду и вопрос.")
            return
        try:
            self.score_service.set_question_score(team_id, question_id, self.question_points_input.value())
        except ValueError as error:
            QMessageBox.warning(self, "Очки", str(error))
            return
        self._reload_after_score_change(team_id)

    def _rename_team(self) -> None:
        team_id = self._selected_team_id()
        if team_id is None:
            QMessageBox.warning(self, "Команды", "Сначала выберите команду.")
            return
        try:
            updated_team = self.team_service.update_team(team_id, self.team_name_input.text())
        except ValueError as error:
            QMessageBox.warning(self, "Команды", str(error))
            return
        self.refresh()
        self._restore_team_selection(updated_team.id)
        self.data_changed.emit()

    def _delete_team(self) -> None:
        team_id = self._selected_team_id()
        if team_id is None:
            QMessageBox.warning(self, "Команды", "Сначала выберите команду.")
            return
        team = self.team_service.get_team(team_id)
        if team is None:
            QMessageBox.warning(self, "Команды", "Выбранная команда не найдена.")
            return
        answer = QMessageBox.question(
            self,
            "Удаление команды",
            f"Удалить команду «{team.name}» вместе с её результатами?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.team_service.delete_team(team_id)
        except ValueError as error:
            QMessageBox.warning(self, "Команды", str(error))
            return
        self.refresh()
        self.data_changed.emit()

    def _set_round_adjustment(self) -> None:
        team_id = self._selected_team_id()
        round_id = self.round_combo.currentData()
        if team_id is None or round_id is None:
            QMessageBox.warning(self, "Очки", "Сначала выберите команду и раунд.")
            return
        try:
            self.score_service.set_round_adjustment(
                team_id,
                round_id,
                self.round_adjustment_input.value(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Очки", str(error))
            return
        self._reload_after_score_change(team_id)

    def _set_total_score(self) -> None:
        team_id = self._selected_team_id()
        if team_id is None:
            QMessageBox.warning(self, "Очки", "Сначала выберите команду.")
            return
        try:
            self.score_service.set_total_score(team_id, self.total_score_input.value())
        except ValueError as error:
            QMessageBox.warning(self, "Очки", str(error))
            return
        self._reload_after_score_change(team_id)

    def _reset_team_scores(self) -> None:
        team_id = self._selected_team_id()
        if team_id is None:
            QMessageBox.warning(self, "Очки", "Сначала выберите команду.")
            return
        answer = QMessageBox.question(
            self,
            "Сброс очков команды",
            "Сбросить все очки выбранной команды?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.score_service.reset_team_scores(team_id)
        self._reload_after_score_change(team_id)

    def _reset_game_scores(self) -> None:
        game = self.get_selected_game()
        if game is None:
            QMessageBox.warning(self, "Очки", "Сначала выберите игру.")
            return
        answer = QMessageBox.question(
            self,
            "Сброс результатов",
            "Сбросить все результаты выбранной игры?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.current_session_id is not None:
            self.score_service.reset_scores_for_session(self.current_session_id)
        else:
            self.score_service.reset_scores(game.id)
        self.refresh()
        self.data_changed.emit()

    def _reload_after_score_change(self, preferred_team_id: int) -> None:
        self._load_scores(preferred_team_id=preferred_team_id)
        self.data_changed.emit()

    def _update_question_defaults(self) -> None:
        question_id = self.question_combo.currentData()
        if question_id is None:
            self.question_points_input.setValue(0)
            return
        question = self.question_service.get_question(question_id)
        if question is not None:
            self.question_points_input.setValue(question.points)

    def _selected_team_id(self) -> int | None:
        current_row = self.score_table.currentRow()
        if current_row < 0:
            return None
        item = self.score_table.item(current_row, 1)
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _restore_team_selection(self, team_id: int | None) -> None:
        if self.score_table.rowCount() == 0:
            return
        target_row = 0
        if team_id is not None:
            for row_index in range(self.score_table.rowCount()):
                item = self.score_table.item(row_index, 1)
                if item is not None and item.data(Qt.UserRole) == team_id:
                    target_row = row_index
                    break
        self.score_table.selectRow(target_row)
        self._update_details()

    def _update_details(self) -> None:
        current_row = self.score_table.currentRow()
        if current_row < 0 or current_row >= len(self.scoreboard_rows):
            self.selected_team_label.setText("Выбранная команда: не выбрана")
            self.team_name_input.clear()
            self.details_label.setText("Пока нет выбранной команды.")
            return

        row = self.scoreboard_rows[current_row]
        self.team_name_input.setText(row.team_name)
        self.selected_team_label.setText(f"Выбранная команда: {row.team_name} · место {current_row + 1}")
        round_lines = []
        for round_id, round_score in row.round_scores.items():
            round_item = self.rounds_by_id.get(round_id)
            if round_item is None:
                continue
            round_lines.append(f"{round_item.title}: {round_score}")
        round_total = sum(row.round_scores.values())
        total_adjustment = row.total_score - round_total

        self.total_score_input.setValue(row.total_score)
        self.details_label.setText(
            f"Место: {current_row + 1}\n\n"
            f"Команда: {row.team_name}\n\n"
            f"Итог: {row.total_score}\n\n"
            f"По раундам:\n" + ("\n".join(round_lines) if round_lines else "Пока нет начислений.")
            + (
                f"\n\nОбщая корректировка: {total_adjustment:+d}"
                if total_adjustment != 0
                else ""
            )
        )

    def _handle_score_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading_score_table or item.column() <= 1:
            return

        cell_kind = item.data(self.CELL_KIND_ROLE)
        team_id = item.data(Qt.UserRole)
        if not cell_kind or team_id is None:
            return

        raw_value = item.text().strip()
        try:
            value = int(raw_value)
        except ValueError:
            QMessageBox.warning(self, "Очки", "Введите целое число.")
            self._reload_after_score_change(int(team_id))
            return

        if value < 0:
            QMessageBox.warning(self, "Очки", "Очки не могут быть отрицательными.")
            self._reload_after_score_change(int(team_id))
            return

        try:
            kind, kind_id = cell_kind
            if kind == "round":
                self.score_service.set_round_total(int(team_id), int(kind_id), value)
            elif kind == "total":
                self.score_service.set_total_score(int(team_id), value)
            else:
                return
        except ValueError as error:
            QMessageBox.warning(self, "Очки", str(error))
            self._reload_after_score_change(int(team_id))
            return

        self._reload_after_score_change(int(team_id))

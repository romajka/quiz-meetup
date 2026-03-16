from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from quiz_meetup.config import DEFAULT_TEAM_COLOR
from quiz_meetup.models import Game, Team
from quiz_meetup.services.game_service import GameService
from quiz_meetup.services.team_service import TeamService


class TeamsPage(QWidget):
    data_changed = Signal()

    def __init__(self, game_service: GameService, team_service: TeamService) -> None:
        super().__init__()
        self.game_service = game_service
        self.team_service = team_service
        self.current_team_id: int | None = None
        self.current_session_id: int | None = None
        self.current_session_game_id: int | None = None

        self.game_combo = QComboBox()
        self.game_combo.currentIndexChanged.connect(self._load_teams)

        self.teams_list = QListWidget()
        self.teams_list.itemSelectionChanged.connect(self._update_details)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: Команда Север")

        self.color_input = QLineEdit(DEFAULT_TEAM_COLOR)
        self.color_input.setPlaceholderText("#1F7A8C")

        self.details_label = QLabel("Сначала создайте игру и команду.")
        self.details_label.setWordWrap(True)
        self.details_label.setObjectName("DetailsLabel")

        self.new_button = QPushButton("Новая команда")
        self.new_button.setObjectName("SecondaryButton")
        self.save_button = QPushButton("Сохранить изменения")
        self.save_button.setObjectName("AccentButton")
        self.create_button = QPushButton("Добавить команду")
        self.create_button.setObjectName("AccentButton")
        self.delete_button = QPushButton("Удалить команду")
        self.delete_button.setObjectName("DangerButton")
        self.color_button = QPushButton("Выбрать цвет")
        self.color_button.setObjectName("SecondaryButton")

        self._build_ui()
        self._connect_signals()
        self._clear_form()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setSpacing(16)

        left_card = QFrame()
        left_card.setObjectName("ContentCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(10)
        left_layout.addWidget(QLabel("Игра"))
        left_layout.addWidget(self.game_combo)
        left_layout.addWidget(QLabel("Команды"))
        left_layout.addWidget(self.teams_list, 1)

        color_row = QHBoxLayout()
        color_row.addWidget(self.color_input, 1)
        color_row.addWidget(self.color_button)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)
        actions_row.addWidget(self.new_button)
        actions_row.addWidget(self.delete_button)

        right_card = QFrame()
        right_card.setObjectName("ContentCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(10)
        right_layout.addWidget(QLabel("Название команды"))
        right_layout.addWidget(self.name_input)
        right_layout.addWidget(QLabel("Цвет"))
        right_layout.addLayout(color_row)
        right_layout.addWidget(self.create_button)
        right_layout.addWidget(self.save_button)
        right_layout.addLayout(actions_row)
        right_layout.addSpacing(16)
        right_layout.addWidget(QLabel("Детали"))
        right_layout.addWidget(self.details_label)
        right_layout.addStretch(1)

        for button in (
            self.new_button,
            self.save_button,
            self.create_button,
            self.delete_button,
            self.color_button,
        ):
            button.setMinimumHeight(46)

        layout.addWidget(left_card, 2)
        layout.addWidget(right_card, 3)

    def _connect_signals(self) -> None:
        self.color_button.clicked.connect(self._pick_color)
        self.create_button.clicked.connect(self._create_team)
        self.save_button.clicked.connect(self._save_team)
        self.delete_button.clicked.connect(self._delete_team)
        self.new_button.clicked.connect(self._start_new_team)

    def refresh(self) -> None:
        selected_game_id = self.game_combo.currentData()
        selected_team_id = self._selected_team_id()
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

        self._load_teams()
        self._restore_team_selection(selected_team_id)

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
        self._load_teams()

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.color_input.text() or DEFAULT_TEAM_COLOR), self)
        if color.isValid():
            self.color_input.setText(color.name())

    def _create_team(self) -> None:
        game = self.get_selected_game()
        if game is None:
            QMessageBox.warning(self, "Команды", "Сначала создайте и выберите игру.")
            return

        try:
            created_team = self.team_service.create_team(
                game_id=game.id,
                name=self.name_input.text(),
                color=self.color_input.text(),
                session_id=self.current_session_id,
            )
        except ValueError as error:
            QMessageBox.warning(self, "Команды", str(error))
            return

        self._clear_form()
        self.refresh()
        self._restore_team_selection(created_team.id)
        self.data_changed.emit()

    def _save_team(self) -> None:
        team = self._get_selected_team()
        if team is None:
            QMessageBox.warning(self, "Команды", "Сначала выберите команду для редактирования.")
            return

        try:
            updated_team = self.team_service.update_team(
                team_id=team.id,
                name=self.name_input.text(),
                color=self.color_input.text(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Команды", str(error))
            return

        self.refresh()
        self._restore_team_selection(updated_team.id)
        self.data_changed.emit()

    def _delete_team(self) -> None:
        team = self._get_selected_team()
        if team is None:
            QMessageBox.warning(self, "Команды", "Сначала выберите команду для удаления.")
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
            self.team_service.delete_team(team.id)
        except ValueError as error:
            QMessageBox.warning(self, "Команды", str(error))
            return

        self._clear_form()
        self.refresh()
        self.data_changed.emit()

    def _start_new_team(self) -> None:
        self.teams_list.blockSignals(True)
        self.teams_list.clearSelection()
        self.teams_list.blockSignals(False)
        self._clear_form()
        self._update_details()

    def _load_teams(self) -> None:
        game = self.get_selected_game()
        if (
            self.current_session_id is not None
            and game is not None
            and self.current_session_game_id is not None
            and game.id != self.current_session_game_id
        ):
            self.current_session_id = None
            self.current_session_game_id = None
        if game is None:
            teams = []
        elif self.current_session_id is not None:
            teams = self.team_service.list_teams_by_session(self.current_session_id)
        else:
            teams = self.team_service.list_teams_by_game(game.id)
        sorted_teams = sorted(
            teams,
            key=lambda team: (-team.score, team.name.lower(), team.id),
        )

        self.teams_list.blockSignals(True)
        self.teams_list.clear()
        if game is not None:
            for index, team in enumerate(sorted_teams, start=1):
                item = QListWidgetItem(f"{index}. {team.name}\nИтог: {team.score}")
                item.setData(Qt.UserRole, team.id)
                self.teams_list.addItem(item)
        self.teams_list.blockSignals(False)

        if self.teams_list.count() > 0:
            self.teams_list.setCurrentRow(0)
        self._update_details()

    def _update_details(self) -> None:
        team = self._get_selected_team()
        if team is None:
            self.details_label.setText("Создайте новую команду или выберите существующую слева.")
            self.current_team_id = None
            return

        self.current_team_id = team.id
        self.name_input.setText(team.name)
        self.color_input.setText(team.color)
        place = self._team_place(team.id)
        self.details_label.setText(
            f"Место: {place}\n\n"
            f"Название: {team.name}\n\n"
            f"Цвет: {team.color}\n"
            f"Итоговый счёт: {team.score}\n"
            f"Создано: {team.created_at}"
        )

    def _get_selected_team(self) -> Team | None:
        team_id = self._selected_team_id()
        if team_id is None:
            return None
        return self.team_service.get_team(team_id)

    def _selected_team_id(self) -> int | None:
        item = self.teams_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _restore_team_selection(self, team_id: int | None) -> None:
        if self.teams_list.count() == 0:
            self._clear_form()
            return

        target_row = 0
        if team_id is not None:
            for index in range(self.teams_list.count()):
                if self.teams_list.item(index).data(Qt.UserRole) == team_id:
                    target_row = index
                    break
        self.teams_list.setCurrentRow(target_row)

    def _clear_form(self) -> None:
        self.current_team_id = None
        self.name_input.clear()
        self.color_input.setText(DEFAULT_TEAM_COLOR)

    def _team_place(self, team_id: int) -> int:
        game = self.get_selected_game()
        if game is None:
            return 0

        if self.current_session_id is not None:
            teams = sorted(
                self.team_service.list_teams_by_session(self.current_session_id),
                key=lambda team: (-team.score, team.name.lower(), team.id),
            )
        else:
            teams = sorted(
                self.team_service.list_teams_by_game(game.id),
                key=lambda team: (-team.score, team.name.lower(), team.id),
            )
        for index, team in enumerate(teams, start=1):
            if team.id == team_id:
                return index
        return 0

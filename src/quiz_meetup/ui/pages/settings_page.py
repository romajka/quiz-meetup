from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from quiz_meetup.services.settings_service import SettingsService


class SettingsPage(QWidget):
    data_changed = Signal()

    def __init__(
        self,
        settings_service: SettingsService,
        app_data_dir: Path,
        database_path: Path,
        media_dir: Path,
    ) -> None:
        super().__init__()
        self.settings_service = settings_service
        self.app_data_dir = app_data_dir
        self.database_path = database_path
        self.media_dir = media_dir

        self.venue_name_input = QLineEdit()
        self.venue_name_input.setPlaceholderText("Например: Quiz Meetup Baku")

        self.welcome_subtitle_input = QLineEdit()
        self.welcome_subtitle_input.setPlaceholderText("Текст стартового экрана проектора")

        self.projector_fullscreen_checkbox = QCheckBox(
            "Открывать проектор на весь экран по умолчанию"
        )

        self.app_data_label = QLabel(str(self.app_data_dir))
        self.app_data_label.setWordWrap(True)
        self.app_data_label.setObjectName("DetailsLabel")

        self.database_label = QLabel(str(self.database_path))
        self.database_label.setWordWrap(True)
        self.database_label.setObjectName("DetailsLabel")

        self.media_dir_label = QLabel(str(self.media_dir))
        self.media_dir_label.setWordWrap(True)
        self.media_dir_label.setObjectName("DetailsLabel")

        save_button = QPushButton("Сохранить настройки")
        save_button.setObjectName("AccentButton")
        save_button.clicked.connect(self._save_settings)

        self._build_ui(save_button)

    def _build_ui(self, save_button: QPushButton) -> None:
        layout = QHBoxLayout(self)
        layout.setSpacing(16)

        left_card = QFrame()
        left_card.setObjectName("ContentCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(12)
        left_layout.addWidget(QLabel("Основные настройки"))
        left_layout.addWidget(QLabel("Название площадки"))
        left_layout.addWidget(self.venue_name_input)
        left_layout.addWidget(QLabel("Подзаголовок стартового экрана"))
        left_layout.addWidget(self.welcome_subtitle_input)
        left_layout.addWidget(self.projector_fullscreen_checkbox)
        left_layout.addWidget(save_button)
        left_layout.addStretch(1)

        right_card = QFrame()
        right_card.setObjectName("ContentCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(12)
        right_layout.addWidget(QLabel("Локальное хранилище"))
        right_layout.addWidget(QLabel("Папка данных"))
        right_layout.addWidget(self.app_data_label)
        right_layout.addWidget(QLabel("Файл базы данных"))
        right_layout.addWidget(self.database_label)
        right_layout.addWidget(QLabel("Папка медиа"))
        right_layout.addWidget(self.media_dir_label)
        right_layout.addStretch(1)

        layout.addWidget(left_card, 3)
        layout.addWidget(right_card, 2)

    def refresh(self) -> None:
        settings = self.settings_service.get_settings()
        self.venue_name_input.setText(settings["venue_name"])
        self.welcome_subtitle_input.setText(settings["welcome_subtitle"])
        self.projector_fullscreen_checkbox.setChecked(
            settings["projector_fullscreen_default"] == "1"
        )

    def _save_settings(self) -> None:
        self.settings_service.save_settings(
            {
                "venue_name": self.venue_name_input.text().strip(),
                "welcome_subtitle": self.welcome_subtitle_input.text().strip(),
                "projector_fullscreen_default": "1"
                if self.projector_fullscreen_checkbox.isChecked()
                else "0",
            }
        )
        QMessageBox.information(self, "Настройки", "Настройки сохранены.")
        self.data_changed.emit()

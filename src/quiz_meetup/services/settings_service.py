from __future__ import annotations

from quiz_meetup.repositories import SettingsRepository


class SettingsService:
    DEFAULTS = {
        "venue_name": "",
        "welcome_subtitle": "Локальная система проведения квизов",
        "projector_fullscreen_default": "0",
    }

    def __init__(self, repository: SettingsRepository) -> None:
        self.repository = repository

    def get_settings(self) -> dict[str, str]:
        settings = dict(self.DEFAULTS)
        settings.update(self.repository.list_all())
        return settings

    def save_settings(self, values: dict[str, str]) -> None:
        merged = dict(self.DEFAULTS)
        merged.update(values)
        for key, value in merged.items():
            self.repository.set(key, value)

    def should_open_projector_fullscreen(self) -> bool:
        return self.get_settings()["projector_fullscreen_default"] == "1"

    def get_welcome_subtitle(self) -> str:
        return self.get_settings()["welcome_subtitle"].strip() or self.DEFAULTS["welcome_subtitle"]

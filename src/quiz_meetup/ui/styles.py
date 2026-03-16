from __future__ import annotations

import sys

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication, QStyleFactory

from quiz_meetup.resources import read_text_resource


def _build_application_font() -> QFont:
    platform_candidates = {
        "win32": ["Segoe UI", "Arial"],
        "darwin": ["SF Pro Text", "Helvetica Neue", "Arial"],
    }
    default_candidates = ["Noto Sans", "DejaVu Sans", "Liberation Sans", "Arial"]
    candidates = platform_candidates.get(sys.platform, default_candidates) + default_candidates

    available_families = set(QFontDatabase.families())
    for family in candidates:
        if family in available_families:
            return QFont(family, 10)
    return QFont()


def apply_application_style(application: QApplication) -> None:
    application.setStyle(QStyleFactory.create("Fusion"))
    application.setFont(_build_application_font())
    application.setStyleSheet(read_text_resource("assets", "app.qss"))

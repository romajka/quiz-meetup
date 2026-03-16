from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton


def _interface_dir() -> Path | None:
    candidates: list[Path] = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(getattr(sys, "_MEIPASS")) / "Interface")

    current_file = Path(__file__).resolve()
    candidates.append(current_file.parents[3] / "Interface")
    candidates.append(Path.cwd() / "Interface")

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _icon_path(name: str) -> Path | None:
    interface_dir = _interface_dir()
    if interface_dir is None:
        return None

    file_name = name if name.lower().endswith(".svg") else f"{name}.svg"
    path = interface_dir / file_name
    if path.exists():
        return path
    return None


@lru_cache(maxsize=256)
def interface_icon(name: str, color: str = "#ffffff", size: int = 20) -> QIcon:
    path = _icon_path(name)
    if path is None:
        return QIcon()

    svg_text = path.read_text(encoding="utf-8").replace("currentColor", QColor(color).name())
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not renderer.isValid():
        return QIcon()

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def apply_button_icon(
    button: QPushButton,
    icon_name: str,
    color: str,
    size: int = 18,
) -> None:
    button.setIcon(interface_icon(icon_name, color=color, size=size))
    button.setIconSize(QSize(size, size))

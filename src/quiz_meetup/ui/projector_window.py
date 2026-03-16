from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPoint,
    QPauseAnimation,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QSize,
    Qt,
    QUrl,
    QVariantAnimation,
)
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QSizePolicy,
    QStackedLayout,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from quiz_meetup.services.presentation_service import PresentationService, PresentationState


class ScaledPixmapLabel(QLabel):
    def __init__(self, minimum_height: int = 0) -> None:
        super().__init__()
        self._original_pixmap: QPixmap | None = None
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        if minimum_height > 0:
            self.setMinimumHeight(minimum_height)

    def set_scaled_pixmap(self, pixmap: QPixmap | None) -> None:
        self._original_pixmap = pixmap
        self._update_pixmap()

    def clear_scaled_pixmap(self) -> None:
        self._original_pixmap = None
        self.clear()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_pixmap()

    def _update_pixmap(self) -> None:
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        scaled = self._original_pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)


class CircularTimerWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._progress = 0.0
        self._finished = False
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(420)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(self._apply_progress_value)
        self.setObjectName("ProjectorTimerCircle")
        self.setMinimumSize(130, 130)

    def sizeHint(self) -> QSize:  # noqa: D401
        return QSize(150, 150)

    def set_progress_state(self, progress: float, finished: bool) -> None:
        progress = max(0.0, min(1.0, progress))
        if self._animation.state() == QAbstractAnimation.Running:
            self._animation.stop()
        self._finished = finished
        self._animation.setStartValue(self._progress)
        self._animation.setEndValue(progress)
        self._animation.start()

    def _apply_progress_value(self, value) -> None:
        self._progress = float(value)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)
        base_pen = QPen(QColor(255, 255, 255, 45), 12)
        base_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(base_pen)
        painter.drawArc(rect, 0, 360 * 16)

        if self._finished:
            progress_color = QColor("#fb7185")
        elif self._progress > 0.55:
            progress_color = QColor("#34d399")
        elif self._progress > 0.25:
            progress_color = QColor("#fbbf24")
        else:
            progress_color = QColor("#f97316")

        progress_pen = QPen(progress_color, 12)
        progress_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(progress_pen)
        painter.drawArc(rect, 90 * 16, int(-self._progress * 360 * 16))


class ProjectorWindow(QMainWindow):
    def __init__(self, presentation_service: PresentationService) -> None:
        super().__init__()
        self.presentation_service = presentation_service

        self.background_player: QMediaPlayer | None = None
        self.background_audio: QAudioOutput | None = None
        self.background_video_widget: QVideoWidget | None = None
        self.foreground_player: QMediaPlayer | None = None
        self.foreground_audio: QAudioOutput | None = None
        self.foreground_video_widget: QVideoWidget | None = None
        self.music_player: QMediaPlayer | None = None
        self.music_audio: QAudioOutput | None = None

        self._timer_bar_animation = QPropertyAnimation(self)
        self._active_animations: list[QSequentialAnimationGroup | QParallelAnimationGroup | QPropertyAnimation] = []
        self._last_content_signature: tuple | None = None

        self.setWindowTitle("Quiz Meetup - Проектор")
        self.resize(1366, 900)

        self.screen_stack = QStackedWidget()
        self.screen_stack.setObjectName("ProjectorScreen")
        self.rich_screen = self._build_rich_screen()
        self.score_screen = self._build_score_screen()
        self.winners_screen = self._build_winners_screen()

        self.screen_stack.addWidget(self.rich_screen)
        self.screen_stack.addWidget(self.score_screen)
        self.screen_stack.addWidget(self.winners_screen)
        self.setCentralWidget(self.screen_stack)

        self.transition_overlay = QLabel(self.screen_stack)
        self.transition_overlay.setScaledContents(True)
        self.transition_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.transition_overlay.hide()
        self.transition_opacity = QGraphicsOpacityEffect(self.transition_overlay)
        self.transition_overlay.setGraphicsEffect(self.transition_opacity)

        self._all_animated_widgets = [
            self.rich_logo,
            self.rich_title,
            self.rich_subtitle,
            self.rich_badge,
            self.rich_music_status,
            self.rich_timer_frame,
            self.rich_body,
            self.media_stack,
            self.options_frame,
            *self.option_labels,
            self.answer_label,
            self.rich_footer,
            self.score_logo,
            self.score_title,
            self.score_subtitle,
            self.score_music_status,
            self.score_table,
            self.score_footer,
            self.winners_logo,
            self.winners_title,
            self.winners_subtitle,
            self.winners_music_status,
            *self.winner_cards,
            self.winners_footer,
        ]

        self.presentation_service.state_changed.connect(self.apply_state)
        self.apply_state(self.presentation_service.state)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.transition_overlay.setGeometry(self.screen_stack.rect())

    def _build_rich_screen(self) -> QWidget:
        widget = QWidget()
        layout = QStackedLayout(widget)
        layout.setStackingMode(QStackedLayout.StackAll)

        self.background_stack = QStackedWidget()
        self.background_base = QWidget()
        self.background_base.setObjectName("ProjectorScreen")
        self.background_image = ScaledPixmapLabel()
        self.background_image.setObjectName("ProjectorBackground")
        self.background_image.setStyleSheet("background: transparent;")
        self.background_stack.addWidget(self.background_base)
        self.background_stack.addWidget(self.background_image)

        overlay = QWidget()
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(88, 52, 88, 52)
        overlay_layout.setSpacing(18)

        self.rich_logo = ScaledPixmapLabel(minimum_height=92)
        self.rich_logo.setObjectName("ProjectorLogo")
        self.rich_logo.setMaximumHeight(132)

        self.rich_title = QLabel()
        self.rich_title.setObjectName("ProjectorTitle")
        self.rich_title.setAlignment(Qt.AlignCenter)
        self.rich_title.setWordWrap(True)

        self.rich_subtitle = QLabel()
        self.rich_subtitle.setObjectName("ProjectorSubtitle")
        self.rich_subtitle.setAlignment(Qt.AlignCenter)
        self.rich_subtitle.setWordWrap(True)

        self.rich_badge = QLabel()
        self.rich_badge.setObjectName("ProjectorBadge")
        self.rich_badge.setAlignment(Qt.AlignCenter)
        self.rich_badge.hide()

        self.rich_music_status = QLabel()
        self.rich_music_status.setObjectName("ProjectorMusicStatus")
        self.rich_music_status.setAlignment(Qt.AlignCenter)
        self.rich_music_status.hide()

        self.rich_timer_frame = QFrame()
        self.rich_timer_frame.setObjectName("ProjectorTimerFrame")
        rich_timer_layout = QHBoxLayout(self.rich_timer_frame)
        rich_timer_layout.setContentsMargins(20, 20, 20, 20)
        rich_timer_layout.setSpacing(20)

        self.rich_timer_circle = CircularTimerWidget()

        timer_text_column = QWidget()
        timer_text_layout = QVBoxLayout(timer_text_column)
        timer_text_layout.setContentsMargins(0, 0, 0, 0)
        timer_text_layout.setSpacing(10)

        self.rich_timer_source = QLabel()
        self.rich_timer_source.setObjectName("ProjectorTimerSource")
        self.rich_timer_source.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.rich_timer_source.setWordWrap(True)

        self.rich_timer_value = QLabel("00:00")
        self.rich_timer_value.setObjectName("ProjectorTimerValue")
        self.rich_timer_value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.rich_timer_progress = QProgressBar()
        self.rich_timer_progress.setObjectName("ProjectorTimerProgress")
        self.rich_timer_progress.setRange(0, 100)
        self.rich_timer_progress.setTextVisible(False)

        timer_text_layout.addWidget(self.rich_timer_source)
        timer_text_layout.addWidget(self.rich_timer_value)
        timer_text_layout.addWidget(self.rich_timer_progress)

        rich_timer_layout.addWidget(self.rich_timer_circle, 0, Qt.AlignCenter)
        rich_timer_layout.addWidget(timer_text_column, 1)
        self.rich_timer_frame.hide()

        self.rich_body = QLabel()
        self.rich_body.setObjectName("ProjectorBody")
        self.rich_body.setAlignment(Qt.AlignCenter)
        self.rich_body.setWordWrap(True)

        self.media_stack = QStackedWidget()
        self.media_placeholder = QLabel("Медиа для этого экрана не назначено.")
        self.media_placeholder.setObjectName("ProjectorMediaPlaceholder")
        self.media_placeholder.setAlignment(Qt.AlignCenter)
        self.media_placeholder.setWordWrap(True)

        self.media_image = ScaledPixmapLabel(minimum_height=270)
        self.media_image.setObjectName("ProjectorMediaFrame")
        self.media_image.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.media_stack.addWidget(self.media_placeholder)
        self.media_stack.addWidget(self.media_image)
        self.media_stack.setCurrentWidget(self.media_placeholder)

        self.options_frame = QFrame()
        self.options_frame.setObjectName("ProjectorOptionsFrame")
        options_layout = QGridLayout(self.options_frame)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setHorizontalSpacing(18)
        options_layout.setVerticalSpacing(18)

        self.option_labels: list[QLabel] = []
        for index in range(4):
            label = QLabel()
            label.setObjectName("ProjectorOption")
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignCenter)
            label.hide()
            self.option_labels.append(label)
            options_layout.addWidget(label, index // 2, index % 2)
        self.options_frame.hide()

        self.answer_label = QLabel()
        self.answer_label.setObjectName("ProjectorAnswer")
        self.answer_label.setAlignment(Qt.AlignCenter)
        self.answer_label.setWordWrap(True)
        self.answer_label.hide()

        self.rich_footer = QLabel()
        self.rich_footer.setObjectName("ProjectorFooter")
        self.rich_footer.setAlignment(Qt.AlignCenter)
        self.rich_footer.setWordWrap(True)

        overlay_layout.addWidget(self.rich_logo, alignment=Qt.AlignCenter)
        overlay_layout.addWidget(self.rich_title)
        overlay_layout.addWidget(self.rich_subtitle)
        overlay_layout.addWidget(self.rich_badge, alignment=Qt.AlignCenter)
        overlay_layout.addWidget(self.rich_music_status, alignment=Qt.AlignCenter)
        overlay_layout.addWidget(self.rich_timer_frame)
        overlay_layout.addWidget(self.rich_body)
        overlay_layout.addWidget(self.media_stack, 1)
        overlay_layout.addWidget(self.options_frame)
        overlay_layout.addWidget(self.answer_label)
        overlay_layout.addWidget(self.rich_footer)

        layout.addWidget(self.background_stack)
        layout.addWidget(overlay)
        return widget

    def _build_score_screen(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("ProjectorScreen")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(88, 52, 88, 52)
        layout.setSpacing(22)

        self.score_logo = ScaledPixmapLabel(minimum_height=82)
        self.score_logo.setMaximumHeight(124)

        self.score_title = QLabel()
        self.score_title.setObjectName("ProjectorTitle")
        self.score_title.setAlignment(Qt.AlignCenter)

        self.score_subtitle = QLabel()
        self.score_subtitle.setObjectName("ProjectorSubtitle")
        self.score_subtitle.setAlignment(Qt.AlignCenter)

        self.score_music_status = QLabel()
        self.score_music_status.setObjectName("ProjectorMusicStatus")
        self.score_music_status.setAlignment(Qt.AlignCenter)
        self.score_music_status.hide()

        self.score_table = QTableWidget(0, 2)
        self.score_table.setObjectName("ProjectorScoreTable")
        self.score_table.setHorizontalHeaderLabels(["Команда", "Очки"])
        self.score_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.score_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.score_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section {"
            "background: rgba(255, 255, 255, 0.12);"
            "color: #f8fafc;"
            "border: none;"
            "padding: 16px 14px;"
            "font-weight: 700;"
            "}"
        )
        self.score_table.verticalHeader().setVisible(False)
        self.score_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.score_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.score_table.setFocusPolicy(Qt.NoFocus)
        self.score_table.setShowGrid(False)

        self.score_footer = QLabel()
        self.score_footer.setObjectName("ProjectorFooter")
        self.score_footer.setAlignment(Qt.AlignCenter)
        self.score_footer.setWordWrap(True)

        layout.addWidget(self.score_logo, alignment=Qt.AlignCenter)
        layout.addWidget(self.score_title)
        layout.addWidget(self.score_subtitle)
        layout.addWidget(self.score_music_status, alignment=Qt.AlignCenter)
        layout.addWidget(self.score_table, 1)
        layout.addWidget(self.score_footer)
        return widget

    def _build_winners_screen(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("ProjectorScreen")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(56, 44, 56, 44)
        layout.setSpacing(18)

        self.winners_logo = ScaledPixmapLabel(minimum_height=82)
        self.winners_logo.setMaximumHeight(124)

        self.winners_title = QLabel()
        self.winners_title.setObjectName("ProjectorTitle")
        self.winners_title.setAlignment(Qt.AlignCenter)

        self.winners_subtitle = QLabel()
        self.winners_subtitle.setObjectName("ProjectorSubtitle")
        self.winners_subtitle.setAlignment(Qt.AlignCenter)

        self.winners_music_status = QLabel()
        self.winners_music_status.setObjectName("ProjectorMusicStatus")
        self.winners_music_status.setAlignment(Qt.AlignCenter)
        self.winners_music_status.hide()

        winners_row = QWidget()
        winners_row_layout = QHBoxLayout(winners_row)
        winners_row_layout.setContentsMargins(0, 0, 0, 0)
        winners_row_layout.setSpacing(16)

        self.winner_cards: list[QFrame] = []
        self.winner_place_labels: list[QLabel] = []
        self.winner_team_labels: list[QLabel] = []
        self.winner_score_labels: list[QLabel] = []

        for place in range(1, 6):
            card = QFrame()
            card.setObjectName("ProjectorWinnerCard")
            card.setProperty("champion", place == 1)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(20, 22, 20, 22)
            card_layout.setSpacing(8)

            place_label = QLabel(f"{place} место")
            place_label.setObjectName("ProjectorWinnerPlace")
            place_label.setAlignment(Qt.AlignCenter)

            team_label = QLabel("Команда не определена")
            team_label.setObjectName("ProjectorWinnerTeam")
            team_label.setAlignment(Qt.AlignCenter)
            team_label.setWordWrap(True)

            score_label = QLabel("0 очков")
            score_label.setObjectName("ProjectorWinnerScore")
            score_label.setAlignment(Qt.AlignCenter)

            card_layout.addWidget(place_label)
            card_layout.addWidget(team_label)
            card_layout.addWidget(score_label)

            winners_row_layout.addWidget(card, 1)
            self.winner_cards.append(card)
            self.winner_place_labels.append(place_label)
            self.winner_team_labels.append(team_label)
            self.winner_score_labels.append(score_label)

        self.winners_footer = QLabel()
        self.winners_footer.setObjectName("ProjectorFooter")
        self.winners_footer.setAlignment(Qt.AlignCenter)
        self.winners_footer.setWordWrap(True)

        layout.addWidget(self.winners_logo, alignment=Qt.AlignCenter)
        layout.addWidget(self.winners_title)
        layout.addWidget(self.winners_subtitle)
        layout.addWidget(self.winners_music_status, alignment=Qt.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(winners_row)
        layout.addStretch(1)
        layout.addWidget(self.winners_footer)
        return widget

    def apply_state(self, state: PresentationState) -> None:
        content_signature = self._make_content_signature(state)
        animate_content = content_signature != self._last_content_signature
        snapshot = self._capture_transition_snapshot() if animate_content else None

        self._stop_active_animations()
        self._reset_opacity_effects()

        if state.scene in {"scores", "teams"}:
            self._stop_media_players()
            self._apply_logo(self.score_logo, state.logo_path)
            self.score_title.setText(state.title)
            self.score_subtitle.setText(state.subtitle)
            self.score_footer.setText(state.footer)
            self._apply_music_status(state.music_status)
            self._fill_score_table(state)
            self.screen_stack.setCurrentWidget(self.score_screen)
            if animate_content:
                self._animate_score_screen()
        elif state.scene == "winners":
            self._stop_media_players()
            self._apply_logo(self.winners_logo, state.logo_path)
            self.winners_title.setText(state.title)
            self.winners_subtitle.setText(state.subtitle)
            self.winners_footer.setText(state.footer)
            self._apply_music_status(state.music_status)
            self._fill_winners(state)
            self.screen_stack.setCurrentWidget(self.winners_screen)
            if animate_content:
                self._animate_winners_screen()
        else:
            self._apply_music_status(state.music_status)
            self._apply_rich_state(state)
            self.screen_stack.setCurrentWidget(self.rich_screen)
            if animate_content:
                self._animate_rich_screen(state)

        if animate_content:
            self._animate_scene_transition(snapshot)
        self._last_content_signature = content_signature

    def _apply_rich_state(self, state: PresentationState) -> None:
        self.rich_title.setText(state.title)
        self.rich_subtitle.setText(state.subtitle)
        self.rich_body.setText(state.body)
        self.rich_footer.setText(state.footer)
        self.rich_badge.setText(state.badge)
        self.rich_title.setVisible(bool(state.title))
        self.rich_subtitle.setVisible(bool(state.subtitle))
        self.rich_body.setVisible(bool(state.body))
        self.rich_footer.setVisible(bool(state.footer))
        self.rich_badge.setVisible(bool(state.badge))
        self.answer_label.setText(state.answer_text)
        self.answer_label.setVisible(bool(state.answer_text))

        self._apply_logo(self.rich_logo, state.logo_path)
        self._apply_background_media(state.background_path, state.background_type)
        self._apply_foreground_media(state.media_path, state.media_type)
        self._apply_options(state.options, state.highlighted_option_index)
        self._apply_timer(state)

    def _apply_options(self, options: list[str], highlighted_index: int) -> None:
        has_options = any(option.strip() for option in options)
        self.options_frame.setVisible(has_options)
        for index, label in enumerate(self.option_labels):
            label.setProperty("highlighted", index == highlighted_index)
            self._refresh_style(label)
            if index < len(options) and options[index].strip():
                label.setText(options[index])
                label.show()
            else:
                label.clear()
                label.hide()

    def _apply_logo(self, label: ScaledPixmapLabel, logo_path: str | None) -> None:
        if not logo_path:
            label.hide()
            label.clear_scaled_pixmap()
            return

        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            label.hide()
            label.clear_scaled_pixmap()
            return

        label.set_scaled_pixmap(pixmap)
        label.show()

    def _apply_background_media(
        self,
        background_path: str | None,
        background_type: str | None,
    ) -> None:
        if not background_path or not background_type:
            self.background_stack.setCurrentWidget(self.background_base)
            self._stop_background_media()
            return

        if background_type == "image":
            pixmap = QPixmap(background_path)
            if pixmap.isNull():
                self.background_stack.setCurrentWidget(self.background_base)
            else:
                self.background_image.set_scaled_pixmap(pixmap)
                self.background_stack.setCurrentWidget(self.background_image)
            self._stop_background_media()
            return

        if background_type == "video":
            widget = self._ensure_background_video_widget()
            self.background_stack.setCurrentWidget(widget)
            self._play_background_video(background_path)
            return

        self.background_stack.setCurrentWidget(self.background_base)
        self._stop_background_media()

    def _apply_foreground_media(
        self,
        media_path: str | None,
        media_type: str | None,
    ) -> None:
        if not media_path or not media_type:
            self.media_placeholder.setText("Медиа для этого экрана не назначено.")
            self.media_stack.setCurrentWidget(self.media_placeholder)
            self._stop_foreground_media()
            return

        if media_type == "image":
            pixmap = QPixmap(media_path)
            if pixmap.isNull():
                self.media_placeholder.setText("Не удалось загрузить изображение.")
                self.media_stack.setCurrentWidget(self.media_placeholder)
            else:
                self.media_image.set_scaled_pixmap(pixmap)
                self.media_stack.setCurrentWidget(self.media_image)
            self._stop_foreground_media()
            return

        if media_type == "video":
            widget = self._ensure_foreground_video_widget()
            self.media_stack.setCurrentWidget(widget)
            self._play_foreground_video(media_path)
            return

        if media_type == "audio":
            self.media_placeholder.setText("Сейчас воспроизводится аудиофайл.")
            self.media_stack.setCurrentWidget(self.media_placeholder)
            self._play_foreground_audio(media_path)
            return

        self.media_placeholder.setText("Для этого экрана доступен только визуальный контент.")
        self.media_stack.setCurrentWidget(self.media_placeholder)
        self._stop_foreground_media()

    def _fill_score_table(self, state: PresentationState) -> None:
        headers = state.table_headers or ["#", "Команда", "Всего"]
        self.score_table.clearContents()
        self.score_table.setColumnCount(len(headers))
        self.score_table.setHorizontalHeaderLabels(headers)
        self.score_table.setRowCount(len(state.table_rows))

        for column_index in range(len(headers)):
            resize_mode = QHeaderView.Stretch if column_index == 1 else QHeaderView.ResizeToContents
            self.score_table.horizontalHeader().setSectionResizeMode(column_index, resize_mode)
            header_item = QTableWidgetItem(headers[column_index])
            header_item.setTextAlignment(Qt.AlignCenter)
            header_item.setForeground(QColor("#f8fafc"))
            header_item.setBackground(QColor("#22354f"))
            header_font = header_item.font()
            header_font.setBold(True)
            header_font.setPointSize(13)
            header_item.setFont(header_font)
            self.score_table.setHorizontalHeaderItem(column_index, header_item)

        for row_index, row_values in enumerate(state.table_rows):
            row_color = state.table_row_colors[row_index] if row_index < len(state.table_row_colors) else "#ffffff"
            for column_index, value in enumerate(row_values):
                item = QTableWidgetItem(value)
                if column_index == 1:
                    item.setForeground(QColor(row_color))
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                if row_index < 3:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.score_table.setItem(row_index, column_index, item)
        self.score_table.resizeRowsToContents()

    def _fill_winners(self, state: PresentationState) -> None:
        winners_by_place = {place: (team_name, score, color) for place, team_name, score, color in state.winners}
        for index, place in enumerate((1, 2, 3, 4, 5)):
            team_name, score, color = winners_by_place.get(
                place,
                ("Команда не определена", 0, "#cbd5e1"),
            )
            self.winner_place_labels[index].setText(f"{place} место")
            self.winner_team_labels[index].setText(team_name)
            self.winner_score_labels[index].setText(f"{score} очков")
            self.winner_cards[index].setStyleSheet(
                "border: 1px solid rgba(255,255,255,0.22);"
                "border-radius: 28px;"
                f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(15,23,42,0.74), stop:1 {self._to_rgba(color, 0.22)});"
            )

    def _apply_music_status(self, status: str) -> None:
        for label in (
            self.rich_music_status,
            self.score_music_status,
            self.winners_music_status,
        ):
            label.setText(status)
            label.setVisible(bool(status))

    def _apply_timer(self, state: PresentationState) -> None:
        has_timer = state.timer_total_seconds > 0 and state.scene in {
            "question",
            "answer",
            "waiting",
        }
        self.rich_timer_frame.setVisible(has_timer)
        if not has_timer:
            self.rich_timer_source.clear()
            self.rich_timer_value.setText("00:00")
            self.rich_timer_progress.setValue(0)
            self.rich_timer_circle.set_progress_state(0.0, False)
            self.rich_timer_frame.setProperty("finished", False)
            self.rich_timer_value.setProperty("finished", False)
            self._refresh_style(self.rich_timer_frame)
            self._refresh_style(self.rich_timer_value)
            return

        remaining_seconds = max(state.timer_remaining_seconds, 0)
        progress_fraction = remaining_seconds / state.timer_total_seconds
        progress_value = int(progress_fraction * 100)
        finished = remaining_seconds == 0
        timer_status = state.timer_status or ("Время вышло" if finished else "Готов")

        self.rich_timer_frame.setProperty("finished", finished)
        self.rich_timer_value.setProperty("finished", finished)
        self._refresh_style(self.rich_timer_frame)
        self._refresh_style(self.rich_timer_value)

        self.rich_timer_source.setText(f"{state.timer_source or 'Таймер'} · {timer_status}")
        self.rich_timer_value.setText(self._format_time(remaining_seconds))
        self.rich_timer_circle.set_progress_state(progress_fraction, finished)
        self._animate_timer_bar(progress_value)

    @staticmethod
    def _format_time(seconds: int) -> str:
        minutes, seconds = divmod(max(seconds, 0), 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _animate_timer_bar(self, target_value: int) -> None:
        if self._timer_bar_animation.targetObject() is not self.rich_timer_progress:
            self._timer_bar_animation = QPropertyAnimation(self.rich_timer_progress, b"value", self)
            self._timer_bar_animation.setDuration(420)
            self._timer_bar_animation.setEasingCurve(QEasingCurve.OutCubic)
        else:
            self._timer_bar_animation.stop()
        self._timer_bar_animation.setStartValue(self.rich_timer_progress.value())
        self._timer_bar_animation.setEndValue(target_value)
        self._timer_bar_animation.start()

    def _animate_rich_screen(self, state: PresentationState) -> None:
        widgets: list[QWidget] = [
            self.rich_logo,
            self.rich_title,
            self.rich_subtitle,
            self.rich_badge,
            self.rich_music_status,
            self.rich_timer_frame,
            self.rich_body,
            self.media_stack,
            self.rich_footer,
        ]
        self._animate_widget_batch(widgets, base_delay=0, step=56, offset_y=22, scale_inset=14)

        if self.options_frame.isVisible():
            delay = 200
            for index, option_label in enumerate(self.option_labels):
                if option_label.isVisible():
                    self._animate_widget_in(
                        option_label,
                        delay_ms=delay + (index * 70),
                        offset_y=18,
                        duration=300,
                        scale_inset=12,
                    )

        if self.answer_label.isVisible():
            self._animate_widget_in(
                self.answer_label,
                delay_ms=250 if state.scene == "answer" else 120,
                offset_y=14,
                duration=340,
                scale_inset=12,
            )

    def _animate_score_screen(self) -> None:
        self._animate_widget_batch(
            [
                self.score_logo,
                self.score_title,
                self.score_subtitle,
                self.score_music_status,
                self.score_table,
                self.score_footer,
            ],
            base_delay=0,
            step=64,
            offset_y=24,
            scale_inset=14,
        )

    def _animate_winners_screen(self) -> None:
        self._animate_widget_batch(
            [
                self.winners_logo,
                self.winners_title,
                self.winners_subtitle,
                self.winners_music_status,
            ],
            base_delay=0,
            step=60,
            offset_y=22,
            scale_inset=12,
        )
        for index, card in enumerate(self.winner_cards):
            self._animate_widget_in(
                card,
                delay_ms=180 + (index * 90),
                offset_y=26,
                duration=360,
                scale_inset=18,
            )
        self._animate_widget_in(
            self.winners_footer,
            delay_ms=440,
            offset_y=18,
            duration=300,
            scale_inset=10,
        )

    def _animate_widget_batch(
        self,
        widgets: list[QWidget],
        base_delay: int,
        step: int,
        offset_y: int,
        scale_inset: int,
    ) -> None:
        delay = base_delay
        for widget in widgets:
            if widget.isVisible():
                self._animate_widget_in(
                    widget,
                    delay_ms=delay,
                    offset_y=offset_y,
                    duration=320,
                    scale_inset=scale_inset,
                )
                delay += step

    def _animate_widget_in(
        self,
        widget: QWidget,
        delay_ms: int,
        offset_y: int,
        duration: int,
        scale_inset: int,
    ) -> None:
        if not widget.isVisible():
            return

        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        final_geometry = widget.geometry()
        if final_geometry.width() <= 0 or final_geometry.height() <= 0:
            effect.setOpacity(1.0)
            return

        start_geometry = final_geometry.adjusted(
            scale_inset,
            scale_inset,
            -scale_inset,
            -scale_inset,
        ).translated(QPoint(0, offset_y))
        widget.setGeometry(start_geometry)

        opacity_animation = QPropertyAnimation(effect, b"opacity", self)
        opacity_animation.setDuration(duration)
        opacity_animation.setStartValue(0.0)
        opacity_animation.setEndValue(1.0)
        opacity_animation.setEasingCurve(QEasingCurve.OutCubic)

        geometry_animation = QPropertyAnimation(widget, b"geometry", self)
        geometry_animation.setDuration(duration)
        geometry_animation.setStartValue(start_geometry)
        geometry_animation.setEndValue(final_geometry)
        geometry_animation.setEasingCurve(QEasingCurve.OutCubic)

        opacity_sequence = QSequentialAnimationGroup(self)
        geometry_sequence = QSequentialAnimationGroup(self)
        if delay_ms > 0:
            opacity_sequence.addAnimation(QPauseAnimation(delay_ms))
            geometry_sequence.addAnimation(QPauseAnimation(delay_ms))
        opacity_sequence.addAnimation(opacity_animation)
        geometry_sequence.addAnimation(geometry_animation)

        group = QParallelAnimationGroup(self)
        group.addAnimation(opacity_sequence)
        group.addAnimation(geometry_sequence)
        group.finished.connect(lambda w=widget, rect=final_geometry: w.setGeometry(rect))
        group.finished.connect(lambda animation=group: self._release_animation(animation))
        self._keep_animation(group)
        group.start()

    def _animate_scene_transition(self, snapshot: QPixmap | None) -> None:
        if snapshot is None or snapshot.isNull():
            self.transition_overlay.hide()
            return

        self.transition_overlay.setPixmap(snapshot)
        self.transition_overlay.setGeometry(self.screen_stack.rect())
        self.transition_opacity.setOpacity(1.0)
        self.transition_overlay.show()
        self.transition_overlay.raise_()

        fade = QPropertyAnimation(self.transition_opacity, b"opacity", self)
        fade.setDuration(320)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        fade.finished.connect(self.transition_overlay.hide)
        fade.finished.connect(lambda animation=fade: self._release_animation(animation))
        self._keep_animation(fade)
        fade.start()

    def _capture_transition_snapshot(self) -> QPixmap | None:
        if not self.isVisible() or self.screen_stack.width() <= 0 or self.screen_stack.height() <= 0:
            return None
        pixmap = self.screen_stack.grab()
        if pixmap.isNull():
            return None
        return pixmap

    def _ensure_opacity_effect(self, widget: QWidget) -> QGraphicsOpacityEffect:
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            effect.setOpacity(1.0)
            widget.setGraphicsEffect(effect)
        return effect

    def _reset_opacity_effects(self) -> None:
        for widget in self._all_animated_widgets:
            effect = widget.graphicsEffect()
            if isinstance(effect, QGraphicsOpacityEffect):
                effect.setOpacity(1.0)

    def _stop_active_animations(self) -> None:
        for animation in self._active_animations:
            animation.stop()
        self._active_animations.clear()
        self.transition_overlay.hide()

    def _keep_animation(self, animation) -> None:
        self._active_animations.append(animation)

    def _release_animation(self, animation) -> None:
        if animation in self._active_animations:
            self._active_animations.remove(animation)

    @staticmethod
    def _refresh_style(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    def _make_content_signature(self, state: PresentationState) -> tuple:
        winners_signature = tuple(state.winners)
        rows_signature = tuple(tuple(row) for row in state.table_rows)
        headers_signature = tuple(state.table_headers)
        options_signature = tuple(state.options)
        return (
            state.scene,
            state.title,
            state.subtitle,
            state.body,
            state.footer,
            state.badge,
            options_signature,
            state.highlighted_option_index,
            state.answer_text,
            headers_signature,
            rows_signature,
            winners_signature,
            state.logo_path,
            state.background_path,
            state.background_type,
            state.media_path,
            state.media_type,
        )

    @staticmethod
    def _to_rgba(color: str, alpha: float) -> str:
        qcolor = QColor(color)
        qcolor.setAlphaF(alpha)
        return qcolor.name(QColor.HexArgb)

    def _ensure_background_video_widget(self) -> QVideoWidget:
        if self.background_video_widget is None:
            self.background_video_widget = QVideoWidget()
            self.background_video_widget.setObjectName("ProjectorVideoFrame")
            self.background_stack.addWidget(self.background_video_widget)
        return self.background_video_widget

    def _ensure_foreground_video_widget(self) -> QVideoWidget:
        if self.foreground_video_widget is None:
            self.foreground_video_widget = QVideoWidget()
            self.foreground_video_widget.setObjectName("ProjectorVideoFrame")
            self.media_stack.addWidget(self.foreground_video_widget)
        return self.foreground_video_widget

    def _ensure_background_player(self) -> QMediaPlayer:
        if self.background_player is None:
            self.background_player = QMediaPlayer(self)
            self.background_audio = QAudioOutput(self)
            self.background_player.setAudioOutput(self.background_audio)
        if self.background_video_widget is not None:
            self.background_player.setVideoOutput(self.background_video_widget)
        return self.background_player

    def _ensure_foreground_player(self) -> QMediaPlayer:
        if self.foreground_player is None:
            self.foreground_player = QMediaPlayer(self)
            self.foreground_audio = QAudioOutput(self)
            self.foreground_audio.setVolume(0.85)
            self.foreground_player.setAudioOutput(self.foreground_audio)
        if self.foreground_video_widget is not None:
            self.foreground_player.setVideoOutput(self.foreground_video_widget)
        return self.foreground_player

    def _ensure_music_player(self) -> QMediaPlayer:
        if self.music_player is None:
            self.music_player = QMediaPlayer(self)
            self.music_audio = QAudioOutput(self)
            self.music_audio.setVolume(0.65)
            self.music_player.setAudioOutput(self.music_audio)
        return self.music_player

    def _play_background_video(self, video_path: str) -> None:
        player = self._ensure_background_player()
        if self.background_video_widget is not None:
            player.setVideoOutput(self.background_video_widget)
        player.setSource(QUrl.fromLocalFile(str(Path(video_path))))
        player.play()

    def _play_foreground_video(self, video_path: str) -> None:
        player = self._ensure_foreground_player()
        if self.foreground_video_widget is not None:
            player.setVideoOutput(self.foreground_video_widget)
        player.setSource(QUrl.fromLocalFile(str(Path(video_path))))
        player.play()

    def _play_foreground_audio(self, audio_path: str) -> None:
        player = self._ensure_foreground_player()
        player.setVideoOutput(None)
        player.setSource(QUrl.fromLocalFile(str(Path(audio_path))))
        player.play()

    def play_background_music(self, audio_path: str) -> None:
        player = self._ensure_music_player()
        player.setSource(QUrl.fromLocalFile(str(Path(audio_path))))
        player.play()

    def stop_background_music(self) -> None:
        if self.music_player is not None:
            self.music_player.stop()

    def _stop_background_media(self) -> None:
        if self.background_player is not None:
            self.background_player.stop()

    def _stop_foreground_media(self) -> None:
        if self.foreground_player is not None:
            self.foreground_player.stop()

    def _stop_media_players(self) -> None:
        self._stop_background_media()
        self._stop_foreground_media()

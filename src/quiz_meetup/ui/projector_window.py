from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPoint,
    QPauseAnimation,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRect,
    QSequentialAnimationGroup,
    QSize,
    QTimer,
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
    QGraphicsDropShadowEffect,
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
        self._animation.setDuration(960)
        self._animation.setEasingCurve(QEasingCurve.Linear)
        self._animation.valueChanged.connect(self._apply_progress_value)
        self.setObjectName("ProjectorTimerCircle")
        self.setMinimumSize(130, 130)

    def sizeHint(self) -> QSize:  # noqa: D401
        return QSize(150, 150)

    def set_progress_state(self, progress: float, finished: bool) -> None:
        progress = max(0.0, min(1.0, progress))
        if self._animation.state() == QAbstractAnimation.Running:
            self._animation.stop()
        smooth_countdown = (
            not finished
            and not self._finished
            and abs(progress - self._progress) <= 0.22
        )
        self._animation.setDuration(960 if smooth_countdown else 220)
        self._animation.setEasingCurve(QEasingCurve.Linear if smooth_countdown else QEasingCurve.OutCubic)
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
        self._question_timer_bar_animation = QPropertyAnimation(self)
        self._active_animations: list[QSequentialAnimationGroup | QParallelAnimationGroup | QPropertyAnimation] = []
        self._last_content_signature: tuple | None = None
        self._locked_normal_geometry: QRect | None = None
        self._suspend_geometry_tracking = False

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
            self.rich_top_left,
            self.rich_top_right,
            self.rich_logo,
            self.rich_title,
            self.rich_subtitle,
            self.rich_badge,
            self.rich_music_status,
            self.rich_timer_frame,
            self.question_timer_frame,
            self.rich_text_panel,
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
        self._track_normal_geometry()

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        self._track_normal_geometry()

    def _build_rich_screen(self) -> QWidget:
        widget = QWidget()
        layout = QStackedLayout(widget)
        layout.setStackingMode(QStackedLayout.StackAll)
        self.rich_screen_layout = layout

        self.background_stack = QStackedWidget()
        self.background_base = QWidget()
        self.background_base.setObjectName("ProjectorScreen")
        self.background_image = ScaledPixmapLabel()
        self.background_image.setObjectName("ProjectorBackground")
        self.background_image.setStyleSheet("background: transparent;")
        self.background_stack.addWidget(self.background_base)
        self.background_stack.addWidget(self.background_image)

        overlay = QWidget()
        self.rich_overlay = overlay
        overlay.setAttribute(Qt.WA_StyledBackground, True)
        overlay.setStyleSheet("background: transparent;")
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(88, 52, 88, 52)
        overlay_layout.setSpacing(18)
        self.rich_overlay_layout = overlay_layout

        top_row = QWidget()
        top_row.setAttribute(Qt.WA_StyledBackground, True)
        top_row.setStyleSheet("background: transparent;")
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(16)

        self.rich_top_left = QLabel()
        self.rich_top_left.setObjectName("ProjectorTopMeta")
        self.rich_top_left.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.rich_top_left.hide()

        self.rich_top_right = QLabel()
        self.rich_top_right.setObjectName("ProjectorTopMeta")
        self.rich_top_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.rich_top_right.hide()

        top_row_layout.addWidget(self.rich_top_left, 1)
        top_row_layout.addWidget(self.rich_top_right, 1)

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
        timer_text_column.setAttribute(Qt.WA_StyledBackground, True)
        timer_text_column.setStyleSheet("background: transparent;")
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

        self.question_timer_frame = QFrame()
        self.question_timer_frame.setObjectName("ProjectorQuestionTimerFrame")
        question_timer_layout = QVBoxLayout(self.question_timer_frame)
        question_timer_layout.setContentsMargins(18, 16, 18, 16)
        question_timer_layout.setSpacing(10)

        question_timer_header = QWidget()
        question_timer_header.setAttribute(Qt.WA_StyledBackground, True)
        question_timer_header.setStyleSheet("background: transparent;")
        question_timer_header_layout = QHBoxLayout(question_timer_header)
        question_timer_header_layout.setContentsMargins(0, 0, 0, 0)
        question_timer_header_layout.setSpacing(12)

        self.question_timer_source = QLabel()
        self.question_timer_source.setObjectName("ProjectorQuestionTimerSource")
        self.question_timer_source.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.question_timer_value = QLabel("00:00")
        self.question_timer_value.setObjectName("ProjectorQuestionTimerValue")
        self.question_timer_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        question_timer_header_layout.addWidget(self.question_timer_source, 1)
        question_timer_header_layout.addWidget(self.question_timer_value, 0)

        self.question_timer_progress = QProgressBar()
        self.question_timer_progress.setObjectName("ProjectorQuestionTimerProgress")
        self.question_timer_progress.setRange(0, 100)
        self.question_timer_progress.setTextVisible(False)

        question_timer_layout.addWidget(question_timer_header)
        question_timer_layout.addWidget(self.question_timer_progress)
        self.question_timer_frame.hide()

        self.rich_body = QLabel()
        self.rich_body.setObjectName("ProjectorBody")
        self.rich_body.setAlignment(Qt.AlignCenter)
        self.rich_body.setWordWrap(True)

        self.rich_text_panel = QLabel()
        self.rich_text_panel.setObjectName("ProjectorBody")
        self.rich_text_panel.setAlignment(Qt.AlignCenter)
        self.rich_text_panel.setWordWrap(True)
        self.rich_text_panel.setTextFormat(Qt.RichText)
        self.rich_text_panel.hide()

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

        overlay_layout.addWidget(top_row)
        overlay_layout.addWidget(self.rich_logo, alignment=Qt.AlignCenter)
        overlay_layout.addWidget(self.rich_title)
        overlay_layout.addWidget(self.rich_subtitle)
        overlay_layout.addWidget(self.rich_badge, alignment=Qt.AlignCenter)
        overlay_layout.addWidget(self.rich_music_status, alignment=Qt.AlignCenter)
        overlay_layout.addWidget(self.rich_timer_frame)
        overlay_layout.addWidget(self.media_stack, 1)
        overlay_layout.addWidget(self.rich_text_panel)
        overlay_layout.addWidget(self.rich_body)
        overlay_layout.addWidget(self.options_frame)
        overlay_layout.addWidget(self.answer_label)
        overlay_layout.addWidget(self.rich_footer)
        overlay_layout.addWidget(self.question_timer_frame)

        layout.addWidget(self.background_stack)
        layout.addWidget(overlay)
        layout.setCurrentWidget(overlay)
        overlay.raise_()
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
        self.score_table.setStyleSheet(
            "QTableWidget#ProjectorScoreTable {"
            "background: rgba(255, 255, 255, 0.08);"
            "color: #f8fafc;"
            "border: 1px solid rgba(255, 255, 255, 0.16);"
            "border-radius: 24px;"
            "gridline-color: rgba(255, 255, 255, 0.08);"
            "font-size: 24px;"
            "padding: 10px;"
            "}"
            "QTableWidget#ProjectorScoreTable::item {"
            "padding: 16px;"
            "border-bottom: 1px solid rgba(255, 255, 255, 0.10);"
            "}"
            "QTableWidget#ProjectorScoreTable QHeaderView::section {"
            "background-color: #22354f;"
            "color: #ffffff;"
            "border: none;"
            "border-bottom: 1px solid rgba(255, 255, 255, 0.12);"
            "padding: 16px 14px;"
            "font-weight: 700;"
            "}"
            "QTableWidget#ProjectorScoreTable QTableCornerButton::section {"
            "background-color: #22354f;"
            "border: none;"
            "border-bottom: 1px solid rgba(255, 255, 255, 0.12);"
            "}"
        )
        self.score_table.horizontalHeader().setMinimumHeight(56)
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
        layout.setContentsMargins(56, 40, 56, 40)
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

        self.winner_cards: list[QFrame] = [None] * 5  # type: ignore[list-item]
        self.winner_place_labels: list[QLabel] = [None] * 5  # type: ignore[list-item]
        self.winner_team_labels: list[QLabel] = [None] * 5  # type: ignore[list-item]
        self.winner_score_labels: list[QLabel] = [None] * 5  # type: ignore[list-item]

        winners_list_widget = QWidget()
        winners_list_widget.setAttribute(Qt.WA_StyledBackground, True)
        winners_list_widget.setStyleSheet("background: transparent;")
        winners_list_layout = QVBoxLayout(winners_list_widget)
        winners_list_layout.setContentsMargins(120, 8, 120, 8)
        winners_list_layout.setSpacing(18)
        for place in (1, 2, 3, 4, 5):
            slot = self._build_winner_slot(place)
            winners_list_layout.addWidget(slot)
        winners_list_layout.addStretch(1)

        self.winners_footer = QLabel()
        self.winners_footer.setObjectName("ProjectorFooter")
        self.winners_footer.setAlignment(Qt.AlignCenter)
        self.winners_footer.setWordWrap(True)

        layout.addWidget(self.winners_logo, alignment=Qt.AlignCenter)
        layout.addWidget(self.winners_title)
        layout.addWidget(self.winners_subtitle)
        layout.addWidget(self.winners_music_status, alignment=Qt.AlignCenter)
        layout.addWidget(winners_list_widget, 1)
        layout.addWidget(self.winners_footer)
        return widget

    def _build_winner_slot(self, place: int) -> QWidget:
        wrapper = QWidget()
        wrapper.setAttribute(Qt.WA_StyledBackground, True)
        wrapper.setStyleSheet("background: transparent;")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("ProjectorWinnerCard")
        card.setProperty("champion", place == 1)
        card.setProperty("placeRank", place)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if place == 1:
            card.setMinimumHeight(126)
        elif place in (2, 3):
            card.setMinimumHeight(108)
        else:
            card.setMinimumHeight(96)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(28, 18, 28, 18)
        card_layout.setSpacing(18)

        place_label = QLabel(f"{place} место")
        place_label.setObjectName("ProjectorWinnerPlace")
        place_label.setAlignment(Qt.AlignCenter)
        place_label.setMinimumWidth(176)

        team_label = QLabel("Команда не определена")
        team_label.setObjectName("ProjectorWinnerTeam")
        team_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        team_label.setWordWrap(True)

        score_label = QLabel("0 очков")
        score_label.setObjectName("ProjectorWinnerScore")
        score_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        score_label.setMinimumWidth(180)

        card_layout.addWidget(place_label, 0)
        card_layout.addWidget(team_label, 1)
        card_layout.addWidget(score_label, 0)

        wrapper_layout.addWidget(card)

        index = place - 1
        self.winner_cards[index] = card
        self.winner_place_labels[index] = place_label
        self.winner_team_labels[index] = team_label
        self.winner_score_labels[index] = score_label
        return wrapper

    def apply_state(self, state: PresentationState) -> None:
        preserve_normal_geometry = self.isVisible() and not self.isFullScreen() and not self.isMaximized()
        previous_geometry = (
            QRect(self._locked_normal_geometry)
            if preserve_normal_geometry and self._locked_normal_geometry is not None
            else QRect(self.geometry()) if preserve_normal_geometry else None
        )
        self._active_scene = state.scene
        has_highlighted_option_answer = (
            state.scene == "answer"
            and state.highlighted_option_index >= 0
            and any(option.strip() for option in state.options)
        )
        content_signature = self._make_content_signature(state)
        animate_content = (
            self.isVisible()
            and self._last_content_signature is not None
            and content_signature != self._last_content_signature
            and state.scene == "answer"
            and not has_highlighted_option_answer
        )
        snapshot = None

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
            if hasattr(self, "rich_overlay"):
                self.rich_overlay.raise_()
            if has_highlighted_option_answer and 0 <= state.highlighted_option_index < len(self.option_labels):
                highlighted_label = self.option_labels[state.highlighted_option_index]
                if highlighted_label.isVisible():
                    self._animate_correct_option(highlighted_label, delay_ms=80)
            if animate_content:
                self._animate_rich_screen(state)

        self._last_content_signature = content_signature
        if previous_geometry is not None:
            self._restore_normal_geometry(previous_geometry)

    def _track_normal_geometry(self) -> None:
        if self._suspend_geometry_tracking:
            return
        if not self.isVisible() or self.isFullScreen() or self.isMaximized():
            return
        self._locked_normal_geometry = QRect(self.geometry())

    def _restore_normal_geometry(self, geometry: QRect) -> None:
        if self.isFullScreen() or self.isMaximized():
            return

        def apply_restore() -> None:
            if self.isFullScreen() or self.isMaximized():
                return
            self._suspend_geometry_tracking = True
            try:
                self.setGeometry(geometry)
                self._locked_normal_geometry = QRect(geometry)
            finally:
                self._suspend_geometry_tracking = False

        apply_restore()
        QTimer.singleShot(0, apply_restore)

    def _apply_rich_state(self, state: PresentationState) -> None:
        is_round_scene = state.scene == "round"
        is_question_scene = state.scene == "question"
        is_answer_scene = state.scene == "answer"
        is_centered_info_scene = state.scene in {"welcome", "waiting", "game", "empty"} and not state.media_path
        emphasize_media = bool(state.media_path) and state.emphasize_media and state.scene in {"question", "answer"}
        has_highlighted_option_answer = (
            state.scene == "answer"
            and state.highlighted_option_index >= 0
            and any(option.strip() for option in state.options)
        )
        is_featured_open_answer = (
            is_answer_scene
            and not has_highlighted_option_answer
            and bool(state.answer_text.strip())
        )
        self.rich_top_left.setText(state.top_left_text)
        self.rich_top_right.setText(state.top_right_text)
        self.rich_top_left.setVisible(bool(state.top_left_text) and not is_featured_open_answer)
        self.rich_top_right.setVisible(bool(state.top_right_text) and not is_featured_open_answer)
        self.rich_title.setText(state.title)
        self.rich_subtitle.setText(state.subtitle)
        self.rich_body.setText(state.body)
        self.rich_footer.setText(state.footer)
        self.rich_badge.setText(state.badge)
        self.rich_title.setVisible(False)
        self.rich_subtitle.setVisible(False)
        self.rich_body.setVisible(False)
        self.rich_footer.setVisible(False)
        self.rich_badge.setVisible(bool(state.badge))
        self.answer_label.setText(state.answer_text)
        self.answer_label.setProperty("featured", is_featured_open_answer)
        self._refresh_style(self.answer_label)
        self.answer_label.setVisible(bool(state.answer_text) and not has_highlighted_option_answer)
        self.rich_text_panel.setText(self._build_rich_text_html(state))
        self.rich_text_panel.setVisible(
            bool(state.title or state.subtitle or state.body or state.footer)
            and not is_featured_open_answer
        )
        if is_round_scene:
            self.rich_text_panel.setMinimumHeight(max(420, self.height() // 2))
            self.rich_text_panel.setMaximumHeight(16777215)
            self.rich_text_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        elif is_question_scene:
            self.rich_text_panel.setMinimumHeight(110 if emphasize_media else max(300, self.height() // 3))
            self.rich_text_panel.setMaximumHeight(220 if emphasize_media else 16777215)
            self.rich_text_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        elif is_featured_open_answer:
            self.rich_text_panel.setMinimumHeight(0)
            self.rich_text_panel.setMaximumHeight(0)
            self.rich_text_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        elif is_answer_scene and emphasize_media:
            self.rich_text_panel.setMinimumHeight(120)
            self.rich_text_panel.setMaximumHeight(180)
            self.rich_text_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            self.rich_text_panel.setMinimumHeight(0)
            self.rich_text_panel.setMaximumHeight(16777215)
            self.rich_text_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        if is_featured_open_answer:
            self.answer_label.setMinimumHeight(max(360, self.height() // 2))
            self.answer_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            self.answer_label.setMinimumHeight(0)
            self.answer_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._apply_logo(self.rich_logo, state.logo_path)
        if is_question_scene or is_answer_scene:
            self.rich_logo.hide()
        self._apply_background_media(state.background_path, state.background_type)
        if is_round_scene:
            self.media_stack.setVisible(False)
            self._stop_foreground_media()
        else:
            self._apply_foreground_media(state.media_path, state.media_type)
        self._apply_options(state.options, state.option_media_paths, state.highlighted_option_index)
        self._apply_timer(state)
        self.rich_overlay_layout.setStretchFactor(self.answer_label, 0)
        if is_featured_open_answer:
            self.rich_overlay_layout.setStretchFactor(self.media_stack, 1 if self.media_stack.isVisible() else 0)
            self.rich_overlay_layout.setStretchFactor(self.rich_text_panel, 0)
            self.rich_overlay_layout.setStretchFactor(self.options_frame, 0)
            self.rich_overlay_layout.setStretchFactor(self.answer_label, 1)
            self.media_stack.setMinimumHeight(max(320, self.height() // 3) if self.media_stack.isVisible() else 0)
            self.media_stack.setMaximumHeight(16777215 if self.media_stack.isVisible() else 0)
        elif is_question_scene:
            self.rich_overlay_layout.setStretchFactor(self.media_stack, 3 if emphasize_media else 0)
            self.rich_overlay_layout.setStretchFactor(self.rich_text_panel, 0 if emphasize_media else 1)
            self.rich_overlay_layout.setStretchFactor(self.options_frame, 0)
            if emphasize_media:
                self.media_stack.setMinimumHeight(max(520, int(self.height() * 0.58)))
                self.media_stack.setMaximumHeight(16777215)
            else:
                self.media_stack.setMinimumHeight(0)
                self.media_stack.setMaximumHeight(max(260, self.height() // 2 - 60))
        elif is_answer_scene and emphasize_media:
            self.rich_overlay_layout.setStretchFactor(self.media_stack, 2)
            self.rich_overlay_layout.setStretchFactor(self.rich_text_panel, 0)
            self.rich_overlay_layout.setStretchFactor(self.options_frame, 0)
            self.media_stack.setMinimumHeight(max(500, int(self.height() * 0.56)))
            self.media_stack.setMaximumHeight(16777215)
        elif is_centered_info_scene:
            self.rich_overlay_layout.setStretchFactor(self.media_stack, 0)
            self.rich_overlay_layout.setStretchFactor(self.rich_text_panel, 1)
            self.rich_overlay_layout.setStretchFactor(self.options_frame, 0)
            self.rich_text_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.media_stack.setMinimumHeight(0)
            self.media_stack.setMaximumHeight(0)
        else:
            self.rich_overlay_layout.setStretchFactor(self.media_stack, 1)
            self.rich_overlay_layout.setStretchFactor(self.rich_text_panel, 0)
            self.rich_overlay_layout.setStretchFactor(self.options_frame, 0)
            self.media_stack.setMinimumHeight(0)
            self.media_stack.setMaximumHeight(16777215)

    @staticmethod
    def _build_rich_text_html(state: PresentationState) -> str:
        if state.scene == "round":
            parts: list[str] = ["<div style='text-align:center; max-width:1080px;'>"]
            if state.title:
                parts.append(
                    f"<div style='font-size:118px;font-weight:900;color:#f8fafc;margin-bottom:22px;'>{escape(state.title)}</div>"
                )
            if state.subtitle:
                parts.append(
                    f"<div style='font-size:46px;font-weight:800;color:#d7e7ff;margin-bottom:34px;'>{escape(state.subtitle)}</div>"
                )
            if state.body:
                body_html = "<br>".join(escape(line) for line in state.body.splitlines())
                parts.append(
                    f"<div style='font-size:62px;font-weight:700;color:#edf3ff;line-height:1.28;margin-bottom:36px;'>{body_html}</div>"
                )
            if state.footer:
                parts.append(
                    f"<div style='font-size:31px;font-weight:700;color:#bfd0ea;margin-top:18px;'>{escape(state.footer)}</div>"
                )
            parts.append("</div>")
            return "".join(parts)

        if state.scene == "question":
            question_text = (state.body or state.title).strip()
            if not question_text:
                question_text = "Текст вопроса"
            font_size = ProjectorWindow._question_font_size(
                question_text,
                has_media=bool(state.media_path),
                has_options=bool(state.options),
            )
            return (
                "<div style='text-align:center; max-width:1680px;'>"
                f"<div style='font-size:{font_size}px;font-weight:800;color:#f8fafc;line-height:1.12;margin:0;'>{escape(question_text)}</div>"
                "</div>"
            )

        if state.scene == "answer":
            has_highlighted_option_answer = (
                state.highlighted_option_index >= 0
                and any(option.strip() for option in state.options)
            )
            if has_highlighted_option_answer:
                question_text = (state.body or state.title).strip()
                if not question_text:
                    question_text = "Текст вопроса"
                font_size = ProjectorWindow._question_font_size(
                    question_text,
                    has_media=bool(state.media_path),
                    has_options=True,
                )
                return (
                    "<div style='text-align:center; max-width:1680px;'>"
                    f"<div style='font-size:{font_size}px;font-weight:800;color:#f8fafc;line-height:1.12;margin:0;'>{escape(question_text)}</div>"
                    "</div>"
                )
            return ""

        parts: list[str] = []
        if state.title:
            parts.append(
                f"<div style='font-size:88px;font-weight:900;color:#f8fafc;margin-bottom:18px;'>{escape(state.title)}</div>"
            )
        if state.subtitle:
            parts.append(
                f"<div style='font-size:40px;font-weight:800;color:#d7e7ff;margin-bottom:22px;'>{escape(state.subtitle)}</div>"
            )
        if state.body:
            body_html = "<br>".join(escape(line) for line in state.body.splitlines())
            parts.append(
                f"<div style='font-size:54px;font-weight:700;color:#edf3ff;line-height:1.32;margin-bottom:24px;'>{body_html}</div>"
            )
        if state.footer:
            parts.append(
                f"<div style='font-size:31px;font-weight:700;color:#bfd0ea;margin-top:14px;'>{escape(state.footer)}</div>"
            )
        return "".join(parts)

    @staticmethod
    def _question_font_size(question_text: str, has_media: bool, has_options: bool) -> int:
        text_length = len(question_text)
        if has_options:
            if text_length <= 55:
                return 78
            if text_length <= 100:
                return 66
            return 58
        if has_media:
            if text_length <= 55:
                return 84
            if text_length <= 110:
                return 72
            return 62
        if text_length <= 40:
            return 98
        if text_length <= 80:
            return 86
        if text_length <= 120:
            return 74
        if text_length <= 170:
            return 64
        return 56

    def _apply_options(
        self,
        options: list[str],
        option_media_paths: list[str | None],
        highlighted_index: int,
    ) -> None:
        is_answer_scene = getattr(self, "_active_scene", "") == "answer"
        has_options = any(option.strip() for option in options) or any(
            bool(path) for path in option_media_paths
        )
        self.options_frame.setVisible(has_options)
        for index, label in enumerate(self.option_labels):
            label.setProperty("highlighted", index == highlighted_index)
            label.setProperty(
                "answerCorrect",
                bool(is_answer_scene and index == highlighted_index),
            )
            label.setProperty(
                "answerMuted",
                bool(is_answer_scene and highlighted_index >= 0 and index != highlighted_index),
            )
            effect = label.graphicsEffect()
            if isinstance(effect, QGraphicsDropShadowEffect):
                effect.setBlurRadius(0)
                effect.setOffset(0, 0)
                effect.setColor(QColor(0, 0, 0, 0))
            option_text = options[index] if index < len(options) else ""
            option_media_path = option_media_paths[index] if index < len(option_media_paths) else None
            if option_media_path:
                pixmap = QPixmap(option_media_path)
                if not pixmap.isNull():
                    label.setText("")
                    label.setPixmap(
                        pixmap.scaled(
                            label.size() if label.width() > 0 and label.height() > 0 else QSize(320, 220),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation,
                        )
                    )
                    label.show()
                    self._refresh_style(label)
                    continue
            label.setPixmap(QPixmap())
            if option_text.strip():
                label.setText(option_text)
                label.show()
            else:
                label.clear()
                label.hide()
            self._refresh_style(label)

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
        is_clean_media_scene = getattr(self, "_active_scene", "") == "media"
        if not media_path or not media_type:
            self.media_placeholder.setText("Медиа для этого экрана не назначено.")
            self.media_stack.setCurrentWidget(self.media_placeholder)
            self.media_stack.setVisible(False)
            self._stop_foreground_media()
            return

        self.media_stack.setVisible(True)
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
            self.media_placeholder.setText("" if is_clean_media_scene else "Сейчас воспроизводится аудиофайл.")
            self.media_stack.setCurrentWidget(self.media_placeholder)
            self.media_stack.setVisible(not is_clean_media_scene)
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
                    team_font = item.font()
                    team_font.setBold(True)
                    team_font.setPointSize(18)
                    item.setFont(team_font)
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
            self._apply_winner_card_style(self.winner_cards[index], place, color)
            self._apply_winner_text_style(place, self.winner_place_labels[index], self.winner_team_labels[index], self.winner_score_labels[index])

    def _apply_music_status(self, status: str) -> None:
        for label in (
            self.rich_music_status,
            self.score_music_status,
            self.winners_music_status,
        ):
            label.setText(status)
            label.setVisible(bool(status))

    def _apply_timer(self, state: PresentationState) -> None:
        show_large_timer = state.timer_total_seconds > 0 and state.scene == "waiting"
        show_question_timer = state.timer_total_seconds > 0 and state.scene == "question"
        self.rich_timer_frame.setVisible(show_large_timer)
        self.question_timer_frame.setVisible(show_question_timer)
        self.rich_timer_circle.setVisible(show_large_timer)

        if not (show_large_timer or show_question_timer):
            self.rich_timer_source.clear()
            self.rich_timer_value.setText("00:00")
            self.rich_timer_progress.setValue(0)
            self.question_timer_source.clear()
            self.question_timer_value.setText("00:00")
            self.question_timer_progress.setValue(0)
            self.rich_timer_circle.set_progress_state(0.0, False)
            self.rich_timer_frame.setProperty("finished", False)
            self.rich_timer_value.setProperty("finished", False)
            self.question_timer_frame.setProperty("finished", False)
            self.question_timer_value.setProperty("finished", False)
            self._refresh_style(self.rich_timer_frame)
            self._refresh_style(self.rich_timer_value)
            self._refresh_style(self.question_timer_frame)
            self._refresh_style(self.question_timer_value)
            return

        remaining_seconds = max(state.timer_remaining_seconds, 0)
        progress_fraction = remaining_seconds / state.timer_total_seconds
        progress_value = int(progress_fraction * 100)
        finished = remaining_seconds == 0
        timer_status = state.timer_status or ("Время вышло" if finished else "Готов")

        self.rich_timer_frame.setProperty("finished", finished)
        self.rich_timer_value.setProperty("finished", finished)
        self.question_timer_frame.setProperty("finished", finished)
        self.question_timer_value.setProperty("finished", finished)
        self._refresh_style(self.rich_timer_frame)
        self._refresh_style(self.rich_timer_value)
        self._refresh_style(self.question_timer_frame)
        self._refresh_style(self.question_timer_value)

        self.rich_timer_source.setText(f"{state.timer_source or 'Таймер'} · {timer_status}")
        self.rich_timer_value.setText(self._format_time(remaining_seconds))
        self.question_timer_source.setText(state.timer_source or "Таймер вопроса")
        self.question_timer_value.setText(self._format_time(remaining_seconds))
        self.rich_timer_circle.set_progress_state(progress_fraction, finished)
        smooth_progress = state.timer_status == "running" and not finished
        self._animate_timer_bar(progress_value, smooth=smooth_progress)
        self._animate_question_timer_bar(progress_value, smooth=smooth_progress)

    @staticmethod
    def _format_time(seconds: int) -> str:
        minutes, seconds = divmod(max(seconds, 0), 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _animate_timer_bar(self, target_value: int, *, smooth: bool = False) -> None:
        if self._timer_bar_animation.targetObject() is not self.rich_timer_progress:
            self._timer_bar_animation = QPropertyAnimation(self.rich_timer_progress, b"value", self)
        else:
            self._timer_bar_animation.stop()
        self._timer_bar_animation.setDuration(960 if smooth else 220)
        self._timer_bar_animation.setEasingCurve(QEasingCurve.Linear if smooth else QEasingCurve.OutCubic)
        self._timer_bar_animation.setStartValue(self.rich_timer_progress.value())
        self._timer_bar_animation.setEndValue(target_value)
        self._timer_bar_animation.start()

    def _animate_question_timer_bar(self, target_value: int, *, smooth: bool = False) -> None:
        if self._question_timer_bar_animation.targetObject() is not self.question_timer_progress:
            self._question_timer_bar_animation = QPropertyAnimation(self.question_timer_progress, b"value", self)
        else:
            self._question_timer_bar_animation.stop()
        self._question_timer_bar_animation.setDuration(960 if smooth else 220)
        self._question_timer_bar_animation.setEasingCurve(QEasingCurve.Linear if smooth else QEasingCurve.OutCubic)
        self._question_timer_bar_animation.setStartValue(self.question_timer_progress.value())
        self._question_timer_bar_animation.setEndValue(target_value)
        self._question_timer_bar_animation.start()

    def _animate_correct_option(self, label: QLabel, delay_ms: int = 0) -> None:
        effect = label.graphicsEffect()
        if not isinstance(effect, QGraphicsDropShadowEffect):
            effect = QGraphicsDropShadowEffect(label)
            effect.setOffset(0, 0)
            label.setGraphicsEffect(effect)
        effect.setColor(QColor(45, 212, 191, 220))
        effect.setBlurRadius(12)

        blur_out = QPropertyAnimation(effect, b"blurRadius", self)
        blur_out.setDuration(180)
        blur_out.setStartValue(12)
        blur_out.setEndValue(26)
        blur_out.setEasingCurve(QEasingCurve.OutCubic)

        blur_in = QPropertyAnimation(effect, b"blurRadius", self)
        blur_in.setDuration(220)
        blur_in.setStartValue(26)
        blur_in.setEndValue(16)
        blur_in.setEasingCurve(QEasingCurve.InOutCubic)

        blur_sequence = QSequentialAnimationGroup(self)
        if delay_ms > 0:
            blur_sequence.addAnimation(QPauseAnimation(delay_ms))
        blur_sequence.addAnimation(blur_out)
        blur_sequence.addAnimation(blur_in)
        blur_sequence.finished.connect(lambda animation=blur_sequence: self._release_animation(animation))
        self._keep_animation(blur_sequence)
        blur_sequence.start()

    def _animate_answer_banner(self, label: QLabel, delay_ms: int = 0) -> None:
        final_geometry = label.geometry()
        if final_geometry.width() <= 0 or final_geometry.height() <= 0:
            return

        pulse_geometry = final_geometry.adjusted(-12, -10, 12, 10)

        geometry_out = QPropertyAnimation(label, b"geometry", self)
        geometry_out.setDuration(220)
        geometry_out.setStartValue(final_geometry)
        geometry_out.setEndValue(pulse_geometry)
        geometry_out.setEasingCurve(QEasingCurve.OutCubic)

        geometry_in = QPropertyAnimation(label, b"geometry", self)
        geometry_in.setDuration(260)
        geometry_in.setStartValue(pulse_geometry)
        geometry_in.setEndValue(final_geometry)
        geometry_in.setEasingCurve(QEasingCurve.InOutCubic)

        sequence = QSequentialAnimationGroup(self)
        if delay_ms > 0:
            sequence.addAnimation(QPauseAnimation(delay_ms))
        sequence.addAnimation(geometry_out)
        sequence.addAnimation(geometry_in)
        sequence.finished.connect(lambda w=label, rect=final_geometry: w.setGeometry(rect))
        sequence.finished.connect(lambda animation=sequence: self._release_animation(animation))
        self._keep_animation(sequence)
        sequence.start()

    def _animate_rich_screen(self, state: PresentationState) -> None:
        if state.scene == "answer":
            if self.answer_label.isVisible():
                self._animate_widget_in(
                    self.answer_label,
                    delay_ms=40,
                    offset_y=0,
                    duration=260,
                    scale_inset=0,
                )
            return

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

        opacity_animation = QPropertyAnimation(effect, b"opacity", self)
        opacity_animation.setDuration(duration)
        opacity_animation.setStartValue(0.0)
        opacity_animation.setEndValue(1.0)
        opacity_animation.setEasingCurve(QEasingCurve.OutCubic)

        sequence = QSequentialAnimationGroup(self)
        if delay_ms > 0:
            sequence.addAnimation(QPauseAnimation(delay_ms))
        sequence.addAnimation(opacity_animation)
        sequence.finished.connect(lambda animation=sequence: self._release_animation(animation))
        self._keep_animation(sequence)
        sequence.start()

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
            state.emphasize_media,
        )

    @staticmethod
    def _to_rgba(color: str, alpha: float) -> str:
        qcolor = QColor(color)
        qcolor.setAlphaF(alpha)
        return qcolor.name(QColor.HexArgb)

    def _apply_winner_card_style(self, card: QFrame, place: int, color: str) -> None:
        accent = {
            1: "#facc15",
            2: "#dbe4f0",
            3: "#d39b67",
            4: "#8ad5c4",
            5: "#8ad5c4",
        }.get(place, color)
        border = {
            1: "rgba(254, 240, 138, 0.92)",
            2: "rgba(226, 232, 240, 0.72)",
            3: "rgba(251, 191, 153, 0.72)",
            4: "rgba(153, 246, 228, 0.48)",
            5: "rgba(153, 246, 228, 0.48)",
        }.get(place, "rgba(255,255,255,0.22)")
        background_start = {
            1: "rgba(55, 37, 6, 0.86)",
            2: "rgba(25, 35, 52, 0.84)",
            3: "rgba(56, 31, 17, 0.84)",
            4: "rgba(13, 36, 42, 0.78)",
            5: "rgba(13, 36, 42, 0.78)",
        }.get(place, "rgba(15,23,42,0.74)")
        end_color = self._to_rgba(accent or color, 0.28 if place == 1 else 0.2)
        card.setStyleSheet(
            "QFrame#ProjectorWinnerCard {"
            f"border: {2 if place == 1 else 1}px solid {border};"
            "border-radius: 30px;"
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {background_start}, stop:1 {end_color});"
            "}"
        )

    @staticmethod
    def _apply_winner_text_style(place: int, place_label: QLabel, team_label: QLabel, score_label: QLabel) -> None:
        place_font = place_label.font()
        team_font = team_label.font()
        score_font = score_label.font()

        if place == 1:
            place_font.setPointSize(28)
            place_font.setBold(True)
            team_font.setPointSize(40)
            team_font.setBold(True)
            score_font.setPointSize(28)
            score_font.setBold(True)
        elif place in (2, 3):
            place_font.setPointSize(24)
            place_font.setBold(True)
            team_font.setPointSize(32)
            team_font.setBold(True)
            score_font.setPointSize(24)
            score_font.setBold(True)
        else:
            place_font.setPointSize(21)
            place_font.setBold(True)
            team_font.setPointSize(27)
            team_font.setBold(True)
            score_font.setPointSize(21)
            score_font.setBold(True)

        place_label.setFont(place_font)
        team_label.setFont(team_font)
        score_label.setFont(score_font)

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

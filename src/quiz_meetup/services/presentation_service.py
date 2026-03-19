from __future__ import annotations

from dataclasses import dataclass, field, replace

from PySide6.QtCore import QObject, Signal

from quiz_meetup.models import Game, MediaAsset, Question, Round, ScoreboardRow, Team
from quiz_meetup.services.timer_service import TimerState


@dataclass(slots=True)
class PresentationState:
    scene: str = "welcome"
    title: str = "Quiz Meetup"
    subtitle: str = "Локальная система проведения квизов"
    body: str = "Откройте игру в окне ведущего и выберите, что вывести на проектор."
    footer: str = ""
    badge: str = ""
    top_left_text: str = ""
    top_right_text: str = ""
    options: list[str] = field(default_factory=list)
    option_media_paths: list[str | None] = field(default_factory=list)
    highlighted_option_index: int = -1
    answer_text: str = ""
    table_headers: list[str] = field(default_factory=list)
    table_rows: list[list[str]] = field(default_factory=list)
    table_row_colors: list[str] = field(default_factory=list)
    winners: list[tuple[int, str, int, str]] = field(default_factory=list)
    music_status: str = ""
    timer_total_seconds: int = 0
    timer_remaining_seconds: int = 0
    timer_status: str = ""
    timer_source: str = ""
    logo_path: str | None = None
    background_path: str | None = None
    background_type: str | None = None
    media_path: str | None = None
    media_type: str | None = None


class PresentationService(QObject):
    state_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._state = PresentationState()

    @property
    def state(self) -> PresentationState:
        return self._state

    def show_welcome(
        self,
        subtitle: str | None = None,
        title: str | None = None,
        logo: MediaAsset | None = None,
        background: MediaAsset | None = None,
    ) -> None:
        self._update_state(
            PresentationState(
                scene="welcome",
                title=title or "Quiz Meetup",
                subtitle=subtitle or "Локальная система проведения квизов",
                body="Ведущий готовит следующий экран.",
                footer="Ожидание начала игры",
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
                background_path=background.file_path if background is not None else None,
                background_type=background.media_type if background is not None else None,
            )
        )

    def show_waiting(
        self,
        game: Game,
        logo: MediaAsset | None = None,
        background: MediaAsset | None = None,
    ) -> None:
        self._update_state(
            PresentationState(
                scene="waiting",
                title=game.title,
                subtitle="Пауза / ожидание следующего раунда",
                body=game.description or "Скоро продолжим игру.",
                footer="Подготовка следующего экрана",
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
                background_path=background.file_path if background is not None else None,
                background_type=background.media_type if background is not None else None,
            )
        )

    def show_game(
        self,
        game: Game,
        logo: MediaAsset | None = None,
        background: MediaAsset | None = None,
    ) -> None:
        self._update_state(
            PresentationState(
                scene="game",
                title=game.title,
                subtitle="Начинаем игру",
                body=game.description or "Добро пожаловать на квиз.",
                footer="Quiz Meetup",
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
                background_path=background.file_path if background is not None else None,
                background_type=background.media_type if background is not None else None,
            )
        )

    def show_partner_block(
        self,
        game: Game,
        partner_media: MediaAsset | None,
        logo: MediaAsset | None = None,
    ) -> None:
        self._update_state(
            PresentationState(
                scene="partner",
                title="Партнёры игры",
                subtitle=game.title,
                body="Спасибо партнёрам и спонсорам этого квиза.",
                footer="Партнёрский блок",
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
                media_path=partner_media.file_path if partner_media is not None else None,
                media_type=partner_media.media_type if partner_media is not None else None,
            )
        )

    def show_round(
        self,
        round_item: Round,
        game_title: str,
        logo: MediaAsset | None = None,
        round_media: MediaAsset | None = None,
        footer_text: str | None = None,
    ) -> None:
        self._update_state(
            PresentationState(
                scene="round",
                title=round_item.title,
                subtitle=f"Раунд игры «{game_title}»",
                body=round_item.notes or "Приготовьтесь к следующему раунду.",
                footer=footer_text or "Раунд игры",
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
                media_path=round_media.file_path if round_media is not None else None,
                media_type=round_media.media_type if round_media is not None else None,
            )
        )

    def show_question(
        self,
        question: Question,
        round_title: str,
        options: list[str],
        option_media_paths: list[str | None],
        logo: MediaAsset | None = None,
        question_media: MediaAsset | None = None,
        footer_text: str | None = None,
        top_left_text: str = "",
        top_right_text: str = "",
    ) -> None:
        self._update_state(
            PresentationState(
                scene="question",
                title=question.title,
                subtitle=f"Раунд: {round_title}",
                body=question.prompt,
                footer=footer_text
                or (
                    f"Очки: {question.points} | Таймер: {question.timer_seconds} сек"
                    if question.timer_seconds > 0
                    else f"Очки: {question.points}"
                ),
                top_left_text=top_left_text,
                top_right_text=top_right_text,
                options=options,
                option_media_paths=option_media_paths,
                highlighted_option_index=-1,
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
                media_path=question_media.file_path if question_media is not None else None,
                media_type=question_media.media_type if question_media is not None else None,
            )
        )

    def show_answer(
        self,
        question: Question,
        round_title: str,
        resolved_answer: str,
        options: list[str],
        option_media_paths: list[str | None],
        highlighted_option_index: int = -1,
        logo: MediaAsset | None = None,
        answer_media: MediaAsset | None = None,
        top_left_text: str = "",
        top_right_text: str = "",
    ) -> None:
        self._update_state(
            PresentationState(
                scene="answer",
                title="Правильный ответ",
                subtitle=f"{round_title} / {question.title}",
                body=question.prompt,
                footer="Ответ открыт",
                top_left_text=top_left_text,
                top_right_text=top_right_text,
                options=options,
                option_media_paths=option_media_paths,
                highlighted_option_index=highlighted_option_index,
                answer_text=resolved_answer,
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
                media_path=answer_media.file_path if answer_media is not None else None,
                media_type=answer_media.media_type if answer_media is not None else None,
            )
        )

    def show_scores(
        self,
        game_title: str,
        scoreboard_rows: list[ScoreboardRow],
        round_titles: list[str],
        logo: MediaAsset | None = None,
        totals_only: bool = False,
        title: str = "Таблица очков",
        footer: str | None = None,
    ) -> None:
        headers = ["#", "Команда", "Всего"] if totals_only else ["#", "Команда", *round_titles, "Всего"]
        table_rows: list[list[str]] = []
        table_row_colors: list[str] = []
        for index, row in enumerate(scoreboard_rows, start=1):
            if totals_only:
                table_rows.append([str(index), row.team_name, str(row.total_score)])
            else:
                round_values = [str(value) for value in row.round_scores.values()]
                table_rows.append(
                    [
                        str(index),
                        row.team_name,
                        *round_values,
                        str(row.total_score),
                    ]
                )
            table_row_colors.append(row.team_color)

        self._update_state(
            PresentationState(
                scene="scores",
                title=title,
                subtitle=game_title,
                footer=footer or "Результаты обновляются из окна ведущего",
                table_headers=headers,
                table_rows=table_rows,
                table_row_colors=table_row_colors,
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
            )
        )

    def show_connection_code(
        self,
        game_title: str,
        connection_code: str,
        logo: MediaAsset | None = None,
    ) -> None:
        self._update_state(
            PresentationState(
                scene="game",
                title="Код подключения игроков",
                subtitle=game_title,
                body=(
                    f"{connection_code}\n\n"
                    "Подключение с телефонов будет добавлено в следующих этапах.\n"
                    "Сейчас этот экран можно использовать как сервисный экран для ведущего."
                ),
                footer="Экран подключения",
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
            )
        )

    def show_teams(
        self,
        game_title: str,
        teams: list[Team],
        logo: MediaAsset | None = None,
    ) -> None:
        self._update_state(
            PresentationState(
                scene="teams",
                title="Команды",
                subtitle=game_title,
                footer="Список команд игры",
                table_headers=["#", "Команда"],
                table_rows=[
                    [str(index), team.name]
                    for index, team in enumerate(teams, start=1)
                ],
                table_row_colors=[team.color for team in teams],
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
            )
        )

    def show_media_asset(
        self,
        game_title: str,
        media: MediaAsset,
        logo: MediaAsset | None = None,
    ) -> None:
        is_visual = media.media_type in {"image", "video"}
        self._update_state(
            PresentationState(
                scene="media",
                title="",
                subtitle="",
                body="",
                footer="",
                badge="",
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=None,
                background_path=media.file_path if is_visual else None,
                background_type=media.media_type if is_visual else None,
                media_path=media.file_path if not is_visual else None,
                media_type=media.media_type if not is_visual else None,
            )
        )

    def show_winners(
        self,
        game_title: str,
        winners: list[tuple[int, Team]],
        logo: MediaAsset | None = None,
    ) -> None:
        winner_rows = [(place, team.name, team.score, team.color) for place, team in winners]
        self._update_state(
            PresentationState(
                scene="winners",
                title="Победители",
                subtitle=game_title,
                footer="Поздравляем лучшие команды",
                winners=winner_rows,
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
                logo_path=logo.file_path if logo is not None else None,
            )
        )

    def clear_screen(self) -> None:
        self._update_state(
            PresentationState(
                scene="empty",
                title="Экран очищен",
                body="Выберите следующий экран в окне ведущего.",
                music_status=self._state.music_status,
                timer_total_seconds=self._state.timer_total_seconds,
                timer_remaining_seconds=self._state.timer_remaining_seconds,
                timer_status=self._state.timer_status,
                timer_source=self._state.timer_source,
            )
        )

    def set_music_status(self, status: str) -> None:
        self._update_state(replace(self._state, music_status=status))

    def set_timer_state(self, timer_state: TimerState) -> None:
        self._update_state(
            replace(
                self._state,
                timer_total_seconds=timer_state.total_seconds,
                timer_remaining_seconds=timer_state.remaining_seconds,
                timer_status=timer_state.status_label,
                timer_source=timer_state.source_label,
            )
        )

    def _update_state(self, state: PresentationState) -> None:
        self._state = state
        self.state_changed.emit(state)

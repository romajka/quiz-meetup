from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal


@dataclass(slots=True)
class TimerState:
    total_seconds: int = 0
    remaining_seconds: int = 0
    status: str = "idle"
    source_label: str = ""

    @property
    def status_label(self) -> str:
        return {
            "idle": "Таймер не подготовлен",
            "ready": "Таймер готов к запуску",
            "running": "Таймер идёт",
            "paused": "Таймер на паузе",
            "finished": "Время вышло",
        }.get(self.status, self.status)

    @property
    def display_text(self) -> str:
        minutes, seconds = divmod(max(self.remaining_seconds, 0), 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def progress_percent(self) -> int:
        if self.total_seconds <= 0:
            return 0
        return max(0, min(100, int((self.remaining_seconds / self.total_seconds) * 100)))


class TimerService(QObject):
    state_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._state = TimerState()
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._handle_tick)

    @property
    def state(self) -> TimerState:
        return self._state

    def configure(self, total_seconds: int, source_label: str) -> None:
        normalized_total = max(0, int(total_seconds))
        self._tick_timer.stop()
        self._update_state(
            TimerState(
                total_seconds=normalized_total,
                remaining_seconds=normalized_total,
                status="ready" if normalized_total > 0 else "idle",
                source_label=source_label.strip(),
            )
        )

    def start(self) -> None:
        if self._state.total_seconds <= 0:
            return
        if self._state.status == "paused":
            self.resume()
            return
        if self._state.status == "running":
            return

        remaining_seconds = self._state.remaining_seconds
        if remaining_seconds <= 0:
            remaining_seconds = self._state.total_seconds

        self._tick_timer.start()
        self._update_state(
            TimerState(
                total_seconds=self._state.total_seconds,
                remaining_seconds=remaining_seconds,
                status="running",
                source_label=self._state.source_label,
            )
        )

    def pause(self) -> None:
        if self._state.status != "running":
            return
        self._tick_timer.stop()
        self._update_state(
            TimerState(
                total_seconds=self._state.total_seconds,
                remaining_seconds=self._state.remaining_seconds,
                status="paused",
                source_label=self._state.source_label,
            )
        )

    def resume(self) -> None:
        if self._state.status != "paused" or self._state.remaining_seconds <= 0:
            return
        self._tick_timer.start()
        self._update_state(
            TimerState(
                total_seconds=self._state.total_seconds,
                remaining_seconds=self._state.remaining_seconds,
                status="running",
                source_label=self._state.source_label,
            )
        )

    def reset(self) -> None:
        self._tick_timer.stop()
        self._update_state(
            TimerState(
                total_seconds=self._state.total_seconds,
                remaining_seconds=self._state.total_seconds,
                status="ready" if self._state.total_seconds > 0 else "idle",
                source_label=self._state.source_label,
            )
        )

    def clear(self) -> None:
        self._tick_timer.stop()
        self._update_state(TimerState())

    def _handle_tick(self) -> None:
        remaining_seconds = max(self._state.remaining_seconds - 1, 0)
        status = "running" if remaining_seconds > 0 else "finished"
        if remaining_seconds == 0:
            self._tick_timer.stop()
        self._update_state(
            TimerState(
                total_seconds=self._state.total_seconds,
                remaining_seconds=remaining_seconds,
                status=status,
                source_label=self._state.source_label,
            )
        )

    def _update_state(self, state: TimerState) -> None:
        self._state = state
        self.state_changed.emit(state)

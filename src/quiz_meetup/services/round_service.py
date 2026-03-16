from __future__ import annotations

from quiz_meetup.models import Round
from quiz_meetup.repositories import RoundRepository


class RoundService:
    def __init__(self, repository: RoundRepository) -> None:
        self.repository = repository

    def create_round(
        self,
        game_id: int,
        title: str,
        order_index: int | None,
        timer_seconds: int,
        notes: str,
    ) -> Round:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Название раунда не может быть пустым.")
        next_order_index = (
            order_index
            if order_index is not None
            else self.repository.get_next_order_index(game_id)
        )
        return self.repository.create(
            game_id=game_id,
            title=normalized_title,
            order_index=next_order_index,
            timer_seconds=timer_seconds,
            notes=notes.strip(),
        )

    def update_round(
        self,
        round_id: int,
        title: str,
        timer_seconds: int,
        notes: str,
    ) -> Round:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Название раунда не может быть пустым.")

        updated_round = self.repository.update(
            round_id=round_id,
            title=normalized_title,
            timer_seconds=timer_seconds,
            notes=notes.strip(),
        )
        if updated_round is None:
            raise ValueError("Раунд не найден.")
        return updated_round

    def delete_round(self, round_id: int) -> None:
        round_item = self.repository.get_by_id(round_id)
        if round_item is None:
            raise ValueError("Раунд не найден.")

        game_id = round_item.game_id
        self.repository.delete(round_id)
        self._normalize_orders(game_id)

    def move_round_up(self, round_id: int) -> Round | None:
        return self._move_round(round_id, -1)

    def move_round_down(self, round_id: int) -> Round | None:
        return self._move_round(round_id, 1)

    def list_rounds_by_game(self, game_id: int) -> list[Round]:
        return self.repository.list_by_game(game_id)

    def list_all_rounds(self) -> list[Round]:
        return self.repository.list_all()

    def get_round(self, round_id: int) -> Round | None:
        return self.repository.get_by_id(round_id)

    def _move_round(self, round_id: int, offset: int) -> Round | None:
        round_item = self.repository.get_by_id(round_id)
        if round_item is None:
            raise ValueError("Раунд не найден.")

        rounds = self.repository.list_by_game(round_item.game_id)
        current_index = next(
            (index for index, item in enumerate(rounds) if item.id == round_id),
            None,
        )
        if current_index is None:
            return None

        target_index = current_index + offset
        if target_index < 0 or target_index >= len(rounds):
            return round_item

        current_round = rounds[current_index]
        target_round = rounds[target_index]

        self.repository.update_order(current_round.id, target_round.order_index)
        self.repository.update_order(target_round.id, current_round.order_index)
        return self.repository.get_by_id(round_id)

    def _normalize_orders(self, game_id: int) -> None:
        rounds = self.repository.list_by_game(game_id)
        for order_index, round_item in enumerate(rounds, start=1):
            if round_item.order_index != order_index:
                self.repository.update_order(round_item.id, order_index)

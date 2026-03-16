from __future__ import annotations

from quiz_meetup.models import Question
from quiz_meetup.repositories import QuestionRepository


class QuestionService:
    def __init__(self, repository: QuestionRepository) -> None:
        self.repository = repository

    def create_question(
        self,
        round_id: int,
        title: str | None,
        prompt: str,
        question_type: str,
        notes: str,
        answer: str,
        option_a: str,
        option_b: str,
        option_c: str,
        option_d: str,
        points: int,
        order_index: int | None,
        timer_seconds: int,
    ) -> Question:
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise ValueError("Текст вопроса не может быть пустым.")
        normalized_type = self._normalize_question_type(question_type)
        normalized_options = self._normalize_options(
            question_type=normalized_type,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
        )
        normalized_answer = self._normalize_answer(
            question_type=normalized_type,
            answer=answer,
        )
        normalized_timer = self._normalize_timer(timer_seconds)
        return self.repository.create(
            round_id=round_id,
            title=self._build_title(title, normalized_prompt),
            prompt=normalized_prompt,
            question_type=normalized_type,
            notes=notes.strip(),
            answer=normalized_answer,
            option_a=normalized_options["option_a"],
            option_b=normalized_options["option_b"],
            option_c=normalized_options["option_c"],
            option_d=normalized_options["option_d"],
            points=points,
            order_index=order_index or self.repository.get_next_order_index(round_id),
            timer_seconds=normalized_timer,
        )

    def update_question(
        self,
        question_id: int,
        title: str | None,
        prompt: str,
        question_type: str,
        notes: str,
        answer: str,
        option_a: str,
        option_b: str,
        option_c: str,
        option_d: str,
        points: int,
        timer_seconds: int,
    ) -> Question:
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise ValueError("Текст вопроса не может быть пустым.")

        normalized_type = self._normalize_question_type(question_type)
        normalized_options = self._normalize_options(
            question_type=normalized_type,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
        )
        normalized_answer = self._normalize_answer(
            question_type=normalized_type,
            answer=answer,
        )
        normalized_timer = self._normalize_timer(timer_seconds)

        updated_question = self.repository.update(
            question_id=question_id,
            title=self._build_title(title, normalized_prompt),
            prompt=normalized_prompt,
            question_type=normalized_type,
            notes=notes.strip(),
            answer=normalized_answer,
            option_a=normalized_options["option_a"],
            option_b=normalized_options["option_b"],
            option_c=normalized_options["option_c"],
            option_d=normalized_options["option_d"],
            points=points,
            timer_seconds=normalized_timer,
        )
        if updated_question is None:
            raise ValueError("Вопрос не найден.")
        return updated_question

    def delete_question(self, question_id: int) -> None:
        question = self.repository.get_by_id(question_id)
        if question is None:
            raise ValueError("Вопрос не найден.")

        round_id = question.round_id
        self.repository.delete(question_id)
        self._normalize_orders(round_id)

    def move_question_up(self, question_id: int) -> Question | None:
        return self._move_question(question_id, -1)

    def move_question_down(self, question_id: int) -> Question | None:
        return self._move_question(question_id, 1)

    def list_questions_by_round(self, round_id: int) -> list[Question]:
        return self.repository.list_by_round(round_id)

    def get_question(self, question_id: int) -> Question | None:
        return self.repository.get_by_id(question_id)

    def _move_question(self, question_id: int, offset: int) -> Question | None:
        question = self.repository.get_by_id(question_id)
        if question is None:
            raise ValueError("Вопрос не найден.")

        questions = self.repository.list_by_round(question.round_id)
        current_index = next(
            (index for index, item in enumerate(questions) if item.id == question_id),
            None,
        )
        if current_index is None:
            return None

        target_index = current_index + offset
        if target_index < 0 or target_index >= len(questions):
            return question

        current_question = questions[current_index]
        target_question = questions[target_index]

        self.repository.update_order(current_question.id, target_question.order_index)
        self.repository.update_order(target_question.id, current_question.order_index)
        return self.repository.get_by_id(question_id)

    def _normalize_orders(self, round_id: int) -> None:
        questions = self.repository.list_by_round(round_id)
        for order_index, question in enumerate(questions, start=1):
            if question.order_index != order_index:
                self.repository.update_order(question.id, order_index)

    def _build_title(self, title: str | None, prompt: str) -> str:
        if title is not None and title.strip():
            return title.strip()
        first_line = next((line.strip() for line in prompt.splitlines() if line.strip()), "")
        if not first_line:
            return "Вопрос"
        return first_line[:70]

    def _normalize_question_type(self, question_type: str) -> str:
        normalized_type = question_type.strip().lower()
        if normalized_type not in {"open", "abcd"}:
            raise ValueError("Неизвестный тип вопроса.")
        return normalized_type

    def _normalize_options(
        self,
        question_type: str,
        option_a: str,
        option_b: str,
        option_c: str,
        option_d: str,
    ) -> dict[str, str]:
        normalized = {
            "option_a": option_a.strip(),
            "option_b": option_b.strip(),
            "option_c": option_c.strip(),
            "option_d": option_d.strip(),
        }
        if question_type == "abcd":
            if not all(normalized.values()):
                raise ValueError("Для вопроса ABCD нужно заполнить все четыре варианта ответа.")
        else:
            normalized = {key: "" for key in normalized}
        return normalized

    def _normalize_answer(self, question_type: str, answer: str) -> str:
        normalized_answer = answer.strip()
        if not normalized_answer:
            raise ValueError("Нужно указать правильный ответ.")
        if question_type == "abcd":
            normalized_answer = normalized_answer.upper()
            if normalized_answer not in {"A", "B", "C", "D"}:
                raise ValueError("Для вопроса ABCD правильный ответ должен быть одним из: A, B, C, D.")
        return normalized_answer

    def _normalize_timer(self, timer_seconds: int) -> int:
        if timer_seconds < 0:
            raise ValueError("Таймер вопроса не может быть отрицательным.")
        return timer_seconds

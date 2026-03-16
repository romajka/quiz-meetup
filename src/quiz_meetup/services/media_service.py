from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from quiz_meetup.models import MediaAsset
from quiz_meetup.paths import ApplicationPaths
from quiz_meetup.repositories import MediaRepository


class MediaService:
    SUPPORTED_FORMATS: dict[str, str] = {
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".webp": "image",
        ".mp4": "video",
        ".webm": "video",
        ".mp3": "audio",
        ".wav": "audio",
        ".ogg": "audio",
    }

    ROLE_LABELS: dict[str, str] = {
        "library": "Без привязки",
        "game_splash": "Заставка игры",
        "game_logo": "Логотип",
        "waiting_background": "Фон ожидания",
        "round": "Раунд",
        "question": "Вопрос",
        "answer": "Ответ",
        "sponsor": "Партнёры / спонсоры",
        "background_music": "Фоновая музыка",
    }

    def __init__(self, repository: MediaRepository, paths: ApplicationPaths) -> None:
        self.repository = repository
        self.paths = paths

    def import_media(
        self,
        game_id: int,
        title: str,
        source_path: str,
        usage_role: str = "library",
        round_id: int | None = None,
        question_id: int | None = None,
    ) -> MediaAsset:
        source = Path(source_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise ValueError("Выбранный медиафайл не найден.")
        media_type = self.detect_media_type(source)
        normalized_round_id, normalized_question_id = self.normalize_assignment(
            usage_role=usage_role,
            media_type=media_type,
            round_id=round_id,
            question_id=question_id,
        )

        normalized_title = title.strip() or source.stem

        target_dir = self.paths.media_dir / f"game_{game_id}"
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        safe_name = "".join(
            character if character.isalnum() or character in "._-" else "_"
            for character in source.name
        )
        target_path = target_dir / f"{timestamp}_{safe_name}"
        shutil.copy2(source, target_path)

        return self.repository.create(
            game_id=game_id,
            round_id=normalized_round_id,
            question_id=normalized_question_id,
            usage_role=usage_role,
            media_type=media_type,
            title=normalized_title,
            original_filename=source.name,
            file_path=str(target_path),
        )

    def list_media_by_game(self, game_id: int) -> list[MediaAsset]:
        return self.repository.list_by_game(game_id)

    def get_media(self, media_id: int) -> MediaAsset | None:
        return self.repository.get_by_id(media_id)

    def find_media_for_game(
        self,
        game_id: int,
        usage_role: str,
    ) -> MediaAsset | None:
        media_assets = self.repository.list_by_game(game_id)
        for media in media_assets:
            if media.usage_role == usage_role and media.round_id is None and media.question_id is None:
                return media
        return None

    def find_media_for_round(
        self,
        game_id: int,
        round_id: int,
        usage_role: str = "round",
    ) -> MediaAsset | None:
        media_assets = self.repository.list_by_game(game_id)
        for media in media_assets:
            if media.usage_role == usage_role and media.round_id == round_id:
                return media
        return None

    def find_media_for_question(
        self,
        game_id: int,
        question_id: int,
        usage_role: str,
    ) -> MediaAsset | None:
        media_assets = self.repository.list_by_game(game_id)
        for media in media_assets:
            if media.usage_role == usage_role and media.question_id == question_id:
                return media
        return None

    def set_question_media(
        self,
        game_id: int,
        question_id: int,
        usage_role: str,
        source_path: str,
        title: str,
    ) -> MediaAsset:
        if usage_role not in {"question", "answer"}:
            raise ValueError("Для вопроса можно назначать только медиа вопроса или ответа.")

        created_media = self.import_media(
            game_id=game_id,
            title=title,
            source_path=source_path,
            usage_role=usage_role,
            question_id=question_id,
        )

        for media in self.repository.list_by_game(game_id):
            if media.id == created_media.id:
                continue
            if media.question_id == question_id and media.usage_role == usage_role:
                self.delete_media(media.id)
        return created_media

    def assign_existing_media_to_question(
        self,
        media_id: int,
        question_id: int,
        usage_role: str,
    ) -> MediaAsset:
        if usage_role not in {"question", "answer"}:
            raise ValueError("Для вопроса можно назначать только медиа вопроса или ответа.")

        media = self.repository.get_by_id(media_id)
        if media is None:
            raise ValueError("Выбранный медиафайл не найден.")
        if media.game_id is None:
            raise ValueError("Медиафайл не привязан к игре.")

        for item in self.repository.list_by_game(media.game_id):
            if item.id == media.id:
                continue
            if item.question_id == question_id and item.usage_role == usage_role:
                self.delete_media(item.id)

        updated_media = self.repository.update_metadata(
            media_id=media.id,
            title=media.title,
            usage_role=usage_role,
            round_id=None,
            question_id=question_id,
        )
        if updated_media is None:
            raise ValueError("Не удалось назначить медиафайл.")
        return updated_media

    def clear_question_media(
        self,
        game_id: int,
        question_id: int,
        usage_role: str,
    ) -> None:
        for media in self.repository.list_by_game(game_id):
            if media.question_id == question_id and media.usage_role == usage_role:
                self.delete_media(media.id)

    def update_media_assignment(
        self,
        media_id: int,
        title: str,
        usage_role: str,
        round_id: int | None,
        question_id: int | None,
    ) -> MediaAsset:
        media = self.repository.get_by_id(media_id)
        if media is None:
            raise ValueError("Медиафайл не найден.")

        normalized_round_id, normalized_question_id = self.normalize_assignment(
            usage_role=usage_role,
            media_type=media.media_type,
            round_id=round_id,
            question_id=question_id,
        )
        normalized_title = title.strip() or media.original_filename or Path(media.file_path).stem
        updated_media = self.repository.update_metadata(
            media_id=media_id,
            title=normalized_title,
            usage_role=usage_role,
            round_id=normalized_round_id,
            question_id=normalized_question_id,
        )
        if updated_media is None:
            raise ValueError("Не удалось обновить медиафайл.")
        return updated_media

    def delete_media(self, media_id: int) -> None:
        media = self.repository.get_by_id(media_id)
        if media is None:
            raise ValueError("Медиафайл не найден.")

        path = Path(media.file_path)
        if path.exists():
            path.unlink()
        self.repository.delete(media_id)

    def clone_media_assets(
        self,
        source_game_id: int,
        target_game_id: int,
        round_id_map: dict[int, int] | None = None,
        question_id_map: dict[int, int] | None = None,
    ) -> None:
        round_mapping = round_id_map or {}
        mapping = question_id_map or {}

        for media in self.repository.list_by_game(source_game_id):
            source_path = Path(media.file_path)
            if not source_path.exists():
                continue

            target_dir = self.paths.media_dir / f"game_{target_game_id}"
            target_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            safe_name = "".join(
                character if character.isalnum() or character in "._-" else "_"
                for character in source_path.name
            )
            target_path = target_dir / f"{timestamp}_{safe_name}"
            shutil.copy2(source_path, target_path)

            duplicated_round_id = None
            if media.round_id is not None:
                duplicated_round_id = round_mapping.get(media.round_id)

            duplicated_question_id = None
            if media.question_id is not None:
                duplicated_question_id = mapping.get(media.question_id)

            self.repository.create(
                game_id=target_game_id,
                round_id=duplicated_round_id,
                question_id=duplicated_question_id,
                usage_role=media.usage_role,
                media_type=media.media_type,
                title=media.title,
                original_filename=media.original_filename or source_path.name,
                file_path=str(target_path),
            )

    def remove_game_media(self, game_id: int) -> None:
        for media in self.repository.list_by_game(game_id):
            path = Path(media.file_path)
            if path.exists():
                path.unlink()

        self.repository.delete_by_game(game_id)

        game_media_dir = self.paths.media_dir / f"game_{game_id}"
        if game_media_dir.exists():
            shutil.rmtree(game_media_dir, ignore_errors=True)

    def detect_media_type(self, source_path: Path) -> str:
        extension = source_path.suffix.lower()
        media_type = self.SUPPORTED_FORMATS.get(extension)
        if media_type is None:
            raise ValueError(
                "Неподдерживаемый формат файла. Разрешены: png, jpg, jpeg, webp, mp4, webm, mp3, wav, ogg."
            )
        return media_type

    def normalize_assignment(
        self,
        usage_role: str,
        media_type: str,
        round_id: int | None,
        question_id: int | None,
    ) -> tuple[int | None, int | None]:
        if usage_role not in self.ROLE_LABELS:
            raise ValueError("Неизвестный тип привязки медиа.")

        if usage_role == "round" and round_id is None:
            raise ValueError("Для привязки к раунду нужно выбрать раунд.")
        if usage_role in {"question", "answer"} and question_id is None:
            raise ValueError("Для привязки к вопросу или ответу нужно выбрать вопрос.")
        if usage_role != "round":
            round_id = None
        if usage_role not in {"question", "answer"}:
            question_id = None

        if usage_role == "background_music" and media_type != "audio":
            raise ValueError("Для фоновой музыки можно выбрать только аудиофайл.")
        if usage_role == "game_logo" and media_type != "image":
            raise ValueError("Логотип должен быть изображением.")
        if usage_role in {"game_splash", "sponsor"} and media_type not in {"image", "video"}:
            raise ValueError("Для заставки и спонсорского блока подходят только изображения или видео.")
        if usage_role == "waiting_background" and media_type not in {"image", "video"}:
            raise ValueError("Для фона ожидания подходят только изображения или видео.")
        return round_id, question_id

    def role_label(self, usage_role: str) -> str:
        return self.ROLE_LABELS.get(usage_role, usage_role)

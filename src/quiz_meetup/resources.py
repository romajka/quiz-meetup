from __future__ import annotations

from importlib.resources import files


def read_text_resource(*relative_parts: str, encoding: str = "utf-8") -> str:
    resource = files("quiz_meetup")
    for part in relative_parts:
        resource = resource.joinpath(part)
    return resource.read_text(encoding=encoding)

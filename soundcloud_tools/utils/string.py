import re
from typing import Any


def bold(text: str) -> str:
    return f"__{text}__" if text else text


def clean_artists(artists: str) -> str:
    return re.sub(r"\s+(&|and|x|X)\s+", ", ", artists)


def titelize(string: str) -> str:
    string = string.title()
    return re.sub("dj", "DJ", string, flags=re.IGNORECASE)


def changed_string(old: Any, new: Any) -> str:
    return " ⚠️ " if old != new else ""


def remove_free_dl(title: str):
    return re.sub(r"[\(\[\{]\s*free\s*(dl|download)\s*.*?[\)\]\}]", "", title, flags=re.IGNORECASE).strip()


def remove_parenthesis(title: str):
    return re.sub(r"\[.*?\]", "", title).strip()


def remove_double_spaces(title: str):
    return re.sub(r"\s+", " ", title).strip()


def replace_underscores(title: str):
    return re.sub(r"_", " ", title).strip()


def is_remix(title: str) -> bool:
    return bool(re.search(r"\(.*edit|mix|bootleg|rework.*\)", title, flags=re.IGNORECASE))


def get_mix_name(title: str) -> str | None:
    if match := re.search(r"\((.*)\)", title):
        return match.group(1).strip()
    return None


def get_first_artist(title: str) -> str | None:
    if match := re.match(r"(.*?)\s*-\s*(.*)", title):
        return match.group(1).strip()
    return None


def get_mix_arist(title: str) -> str | None:
    if mix_name := get_mix_name(title):
        return re.sub(r"edit|remix|bootleg|rework|mix", "", mix_name, flags=re.IGNORECASE).strip()
    return None


def clean_title(title: str):
    title = remove_double_spaces(title)
    title.replace("–", "-")  # noqa: RUF001
    title = remove_free_dl(title)
    if is_remix(title):
        return title
    if match := re.match(r"(.*?)\s*-\s*(.*)", title):
        title = match.group(2)
    return title

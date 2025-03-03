import re


def bold(text: str) -> str:
    return f"__{text}__" if text else text


def clean_artists(artists: str) -> str:
    return re.sub(r"\s+(&|and|x|X)\s+", ", ", artists)


def titelize(string: str) -> str:
    string = string.title()
    return re.sub("dj", "DJ", string, flags=re.IGNORECASE)


def changed_string(old: str, new: str) -> bool:
    return " ⚠️ " if old != new else ""


def remove_free_dl(title: str):
    return re.sub(r"[\(\[\{]\s*free\s*(dl|download)\s*.*?[\)\]\}]", "", title, flags=re.IGNORECASE).strip()


def clean_title(title: str):
    title = title.strip()
    title.replace("-", "–")
    title = remove_free_dl(title)
    if "(" in title:
        return title
    if match := re.match(r"(.*?)\s*-\s*(.*)", title):
        title = match.group(2)
    return title

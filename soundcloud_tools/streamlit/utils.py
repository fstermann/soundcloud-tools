import urllib.parse
from pathlib import Path
from typing import Callable

import streamlit as st
from streamlit import session_state as sst
from tabulate import tabulate

from soundcloud_tools.models import Track


def apply_to_sst(func: Callable, key: str) -> Callable:
    def inner():
        sst[key] = func(sst.get(key))

    return inner


def table(data):
    _css = "border: none; vertical-align: top"
    tbl = (
        tabulate(data, tablefmt="unsafehtml")
        .replace('<td style="', f'<td style="{_css} ')
        .replace("<td>", f'<td style="{_css}">')
        .replace('<tr style="', f'<tr style="{_css} ')
        .replace("<tr>", f'<tr style="{_css}">')
    )
    st.write(tbl, unsafe_allow_html=True)


def generate_css(**kwargs):
    return ";".join(f"{k.replace('_', '-')}:{v}" for k, v in kwargs.items())


def load_tracks(folder: Path, file_types: list[str] | None = None):
    files = list(folder.glob("*"))
    files = [
        f
        for f in files
        if f.is_file() and (f.suffix in file_types if file_types else True) and not f.stem.startswith(".")
    ]
    files.sort(key=lambda f: f.name)
    return files


def bold(text: str) -> str:
    return f"__{text}__" if text else text


def render_embedded_track(track: Track):
    options = {
        "url": f"https://api.soundcloud.com/tracks/{track.id}",
        "color": "#ff5500",
        "auto_play": "false",
        "hide_related": "false",
        "show_comments": "true",
        "show_user": "true",
        "show_reposts": "false",
        "show_teaser": "true",
        "visual": "true",
    }
    src_url = f"https://w.soundcloud.com/player/?{urllib.parse.urlencode(options)}"
    div_css = generate_css(
        font_size="10px",
        color="#cccccc",
        line_break="anywhere",
        word_break="normal",
        overflow="hidden",
        white_space="nowrap",
        text_overflow="ellipsis",
        font_family="Interstate,Lucida Grande,Lucida Sans Unicode,Lucida Sans,Garuda,Verdana,Tahoma,sans-serif",
        font_weight="100",
    )
    link_css = generate_css(
        color="#cccccc",
        text_decoration="none",
    )

    st.write(
        f"""\
<iframe width="100%" height="300" scrolling="no" frameborder="no" allow="autoplay" src="{src_url}"></iframe>
<div style="{div_css}">
<a href="{track.user.permalink_url}" title="{track.user.full_name}" target="_blank" style="{link_css}">\
{track.user.full_name}</a>
 ·
<a href="{track.permalink_url}" title="{track.title}" target="_blank" style="{link_css}">{track.title}</a>
</div>""",
        unsafe_allow_html=True,
    )


def reset_track_info_sst():
    for key in sst:
        if key.startswith("ti_"):
            sst[key] = type(sst[key])()

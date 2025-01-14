from pathlib import Path
from typing import Callable

import streamlit as st
from streamlit import session_state as sst
from tabulate import tabulate


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

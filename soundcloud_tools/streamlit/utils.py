from typing import Callable

import streamlit as st
from streamlit import session_state as sst
from tabulate import tabulate

from soundcloud_tools.client import StreamlitClient


@st.cache_resource
def get_client():
    return StreamlitClient()


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
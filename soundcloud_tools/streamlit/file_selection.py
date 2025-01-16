from collections import Counter
from pathlib import Path
from typing import Callable

import streamlit as st
from streamlit import session_state as sst

from soundcloud_tools.streamlit.utils import load_tracks, reset_track_info_sst, table


def file_selector() -> tuple[Path, Path]:
    root_folder = st.text_input("Root folder", value="~/Music/tracks")
    try:
        root_folder = Path(root_folder).expanduser()
        assert root_folder.exists()
    except (AssertionError, FileNotFoundError):
        st.error("Invalid root folder")
        st.stop()

    paths = {
        "Prepare": root_folder / "prepare",
        "Collection": root_folder / "collection",
        "Cleaned": root_folder / "cleaned",
        "Direct": root_folder,
    }
    path = paths[st.radio("Mode", paths, key="mode")]

    if not (files := load_tracks(path)):
        st.error("No files found")
        st.stop()

    with st.container(border=True):
        st.write("__Folder Stats__")
        suffixes = [f.suffix for f in files]
        table(Counter(suffixes).items())

    sst.setdefault("index", 0)

    st.divider()

    st.subheader(":material/playlist_play: File Selection")

    c1, c2 = st.columns(2)

    def wrap_on_click(func: Callable):
        def wrapper():
            func()
            reset_track_info_sst()

        return wrapper

    c1.button(
        ":material/skip_previous: Previous",
        key="prev",
        on_click=wrap_on_click(lambda: sst.__setitem__("index", sst.index - 1)),
        use_container_width=True,
        disabled=sst.get("index") == 0,
    )
    if not 0 <= sst.get("index") < len(files):
        sst.index = 0
    st.selectbox(
        "select",
        files,
        key="selection",
        index=sst.index,
        on_change=wrap_on_click(lambda: sst.__setitem__("index", files.index(sst.selection))),
        label_visibility="collapsed",
        format_func=lambda f: f.name,
    )
    c2.button(
        "Next :material/skip_next:",
        key="next",
        on_click=wrap_on_click(lambda: sst.__setitem__("index", sst.index + 1)),
        use_container_width=True,
        disabled=sst.get("index") == len(files) - 1,
    )

    if "new_track_name" in sst:
        sst.index = files.index(sst.new_track_name)
        if sst.index >= len(files):
            sst.index = 0
        del sst.new_track_name
    try:
        selected_file = files[sst.index]
    except IndexError:
        selected_file = None
    return selected_file, root_folder

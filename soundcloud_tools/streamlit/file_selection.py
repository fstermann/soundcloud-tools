from collections import Counter
from pathlib import Path
from typing import Callable

import streamlit as st
from streamlit import session_state as sst

from soundcloud_tools.streamlit.track_handler import TrackHandler
from soundcloud_tools.streamlit.utils import reset_track_info_sst, table
from soundcloud_tools.utils import load_tracks


def file_selector() -> tuple[Path, Path]:
    with st.container(border=True):
        st.subheader(":material/folder: Folder Selection")
        root_folder, path = render_folder_selection()

        if not (files := load_tracks(path)):
            st.error("No files found")
            st.stop()

        if path.name == "collection":
            if (selected_indices := render_filters(path)) is not None:
                files = [files[i] for i in selected_indices]

        st.divider()

        st.write("__Folder Stats__")
        suffixes = [f.suffix for f in files]
        table(Counter(suffixes).items())

    with st.container(border=True):
        st.subheader(":material/playlist_play: File Selection")
        selected_file = render_file_selection(files)

    return selected_file, root_folder


def render_folder_selection() -> Path:
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
    return root_folder, paths[st.radio("Mode", paths, key="mode")]


def render_filters(path) -> list[int] | None:
    track_infos = TrackHandler.load_track_infos(path)

    # Filter options
    genres = Counter([t.genre for t in track_infos])
    artists = Counter([a for t in track_infos for a in t.artist])

    # Filter components
    search = st.text_input("Search")
    filtered_genres = st.multiselect(
        "Genres", sorted(genres, key=genres.get, reverse=True), format_func=lambda x: f"{x} ({genres[x]})"
    )
    filtered_artists = st.multiselect(
        "Artists", sorted(artists, key=artists.get, reverse=True), format_func=lambda x: f"{x} ({artists[x]})"
    )

    # Filter logic
    selected_indices = [
        i
        for i, t in enumerate(track_infos)
        if t.genre in filtered_genres
        or any(a in t.artist_str for a in filtered_artists)
        or (search and any(search in attr for attr in (t.genre.lower(), t.artist_str.lower(), t.title.lower())))
    ]
    if search and not selected_indices:
        # No results found for search
        return []
    return selected_indices or None


def render_file_selection(files: list[Path]) -> Path | None:
    sst.setdefault("index", 0)

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
    return selected_file

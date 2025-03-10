from collections import Counter
from datetime import date
from pathlib import Path
from typing import Callable

import streamlit as st
from streamlit import session_state as sst

from soundcloud_tools.handler.folder import FolderHandler
from soundcloud_tools.handler.track import TrackHandler
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

    modes = {
        "prepare": "Prepare",
        "collection": "Collection",
        "cleaned": "Cleaned",
        "": "Direct",
    }
    mode = st.radio("Mode", modes, key="mode", format_func=modes.get)
    handler = FolderHandler(folder=root_folder / mode)
    if mode == "cleaned":
        if handler.has_audio_files and st.button("Move All"):
            render_file_moving(handler, target=root_folder / "collection")
    if mode == "prepare":
        handler = FolderHandler(folder=Path.home() / "Downloads")
        filters = [lambda f: FolderHandler.last_modified(f).date() == date.today()]
        if handler.collect_audio_files(*filters) and st.button("Collect All"):
            render_file_moving(handler, target=root_folder / "prepare", filters=filters)
    return root_folder, root_folder / mode


@st.dialog("Move Files", width="large")
def render_file_moving(handler: FolderHandler, target: Path, filters: list[Callable[[Path], bool]] | None = None):
    filters = filters or []
    files = handler.collect_audio_files(*filters)
    st.write(f"Are you sure you want to move {len(files)} files from\n\n`{handler.folder}`\n\nto\n\n`{target}`?")
    st.expander("Files").write(files)
    if st.button("Move All", key="move_all_dialog"):
        handler.move_all_audio_files(target, *filters)
        st.rerun()


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
    start_date = st.date_input("Start Date", value=None) or date.min
    end_date = st.date_input("End Date", value=None) or date.today()

    # Filter logic
    selected_indices = [
        i
        for i, t in enumerate(track_infos)
        if t.genre in filtered_genres
        or any(a in t.artist_str for a in filtered_artists)
        or (search and any(search in attr for attr in (t.genre.lower(), t.artist_str.lower(), t.title.lower())))
        or (start_date <= t.release_date_obj <= end_date)
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

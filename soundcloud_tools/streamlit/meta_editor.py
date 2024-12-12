import asyncio
import re
import urllib.parse
from collections import Counter
from copy import copy
from pathlib import Path
from typing import Callable, Self

import pydub
import requests
import streamlit as st
from mutagen.aiff import AIFF
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3, TCON, TDRC, TDRL, TIT2, TPE1, ID3FileType
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from pydantic import BaseModel, ConfigDict, model_validator
from streamlit import session_state as sst

from soundcloud_tools.models import Track
from soundcloud_tools.streamlit.client import get_client
from soundcloud_tools.streamlit.utils import apply_to_sst, generate_css, table
from soundcloud_tools.utils import convert_to_int

FILETYPE_MAP = {
    ".mp3": MP3,
    ".aif": AIFF,
    ".aiff": AIFF,
    ".wav": WAVE,
}

ARTWORK_WIDTH = 100

st.set_page_config(page_title="MetaEditor", page_icon=":material/database:", layout="wide")


class TrackInfo(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    title: str
    artist: str | list[str]
    genre: str
    year: int
    release_date: str
    artwork: bytes | None = None
    artwork_url: str | None = None

    @model_validator(mode="after")
    def check_artwork_url(self):
        if self.artwork_url and not self.artwork:
            self.artwork = requests.get(self.artwork_url).content
        return self

    @property
    def filename(self) -> str:
        return f"{self.artist_str} - {self.title}"

    @property
    def complete(self) -> bool:
        return all([self.title, self.artist, self.genre, self.year, self.release_date, self.artwork])

    @property
    def artist_str(self) -> str:
        artists = [self.artist] if isinstance(self.artist, str) else self.artist
        return ", ".join(artists)

    @classmethod
    def from_sc_track(cls, track: Track) -> Self:
        artists = (track.publisher_metadata and track.publisher_metadata.artist) or track.user.username
        return cls(
            title=track.title,
            artist=artists,
            genre=track.genre or "",
            year=track.display_date.year,
            release_date=track.display_date.strftime("%Y-%m-%d"),
            artwork_url=track.hq_artwork_url,
        )


class TrackHandler(BaseModel):
    root_folder: Path
    file: Path
    bitrate: int = 320

    @property
    def cleaned_folder(self):
        return self.root_folder / "cleaned"

    @property
    def prepare_folder(self):
        return self.root_folder / "prepare"

    @property
    def archive_folder(self):
        return self.root_folder / "archive"

    def delete(self):
        self.file.unlink()
        return

    @property
    def mp3_file(self):
        return self.cleaned_folder / (self.file.stem + ".mp3")

    @property
    def track(self):
        class_ = FILETYPE_MAP.get(Path(self.file).suffix, EasyID3)
        obj = class_(self.file)
        if not hasattr(obj, "tags") or obj.tags is None:
            obj.add_tags()
        return obj

    @property
    def track_info(self):
        return TrackInfo(
            title=str(self.track.tags.get("TIT2", "")),
            artist=str(self.track.tags.get("TPE1", "")).split("\u0000"),
            genre=str(self.track.tags.get("TCON", "")),
            year=convert_to_int(str(self.track.tags.get("TDRC", 0)), default=0),
            release_date=str(self.track.tags.get("TDRL", "")),
            artwork=self.get_single_cover(raise_error=False),
        )

    @property
    def covers(self):
        return self.track.tags.getall("APIC")

    def get_single_cover(self, raise_error: bool = True):
        if len(self.covers) != 1:
            if raise_error:
                raise ValueError("Track has more than one cover")
            return self.covers[0].data if self.covers else None
        return self.covers[0].data

    def convert_to_mp3(self):
        if not self.cleaned_folder.exists():
            self.cleaned_folder.mkdir(parents=True)
        sound = pydub.AudioSegment.from_file(self.file)
        sound.export(self.mp3_file, format="mp3", bitrate=f"{self.bitrate}k")
        return self.mp3_file

    def move_to_cleaned(self):
        if not self.cleaned_folder.exists():
            self.cleaned_folder.mkdir(parents=True)
        safe_name = self.file.name.replace("/", "-")
        self.file.rename(self.cleaned_folder / safe_name)

    def update_release_date(self, release_date: str):
        track = self.track
        track.tags.delall("TDRL")
        track.tags.add(TDRL(encoding=3, text=release_date))
        track.save()

    def _add_info(self, track, info: TrackInfo, artwork: bytes | None = None):
        track.add(TIT2(encoding=3, text=info.title))
        track.add(TPE1(encoding=3, text=info.artist))
        track.add(TCON(encoding=3, text=info.genre))
        track.add(TDRC(encoding=3, text=str(info.year)))
        track.add(TDRL(encoding=3, text=info.release_date))
        if artwork:
            track.delall("APIC")
            track.add(
                APIC(
                    encoding=0,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=artwork,
                )
            )

    def add_info(self, info: TrackInfo, artwork: bytes | None = None):
        track = self.track
        self._add_info(track.tags, info=info, artwork=artwork)
        track.save()

    def add_mp3_info(self):
        track = ID3(str(self.mp3_file))
        self._add_info(track, info=self.track_info, artwork=self.get_single_cover())
        track.save()

    def archive(self):
        if not self.archive_folder.exists():
            self.archive_folder.mkdir(parents=True)
        self.file.rename(self.archive_folder / self.file.name)

    def rename(self, new_name: str):
        return self.file.rename(Path(self.file.parent, new_name + self.file.suffix))


def load_tracks(folder: Path, file_types: list[str] | None = None):
    files = list(folder.glob("*"))
    files = [
        f
        for f in files
        if f.is_file() and (f.suffix in file_types if file_types else True) and not f.stem.startswith(".")
    ]
    files.sort(key=lambda f: f.name)
    return files


def reset_track_info_sst():
    for key in sst:
        if key.startswith("ti_"):
            sst[key] = type(sst[key])()


@st.dialog("Delete")
def delete_file(handler: TrackHandler):
    if st.button("Delete", key="del_inner"):
        handler.delete()
        st.success("Deleted Successfully")
        st.rerun()


def render_file(file: Path, root_folder: Path):
    st.write(f"### $\\;\\tiny\\textsf{{{file.parent}}}/$ {file.name}")
    handler = TrackHandler(root_folder=root_folder, file=file)
    if not sst.get("ti_title"):
        copy_track_info(handler.track_info)

    with open(file, "rb") as f:
        st.audio(f)

    st.divider()

    # Metadata
    with st.sidebar.container(border=True):
        sc_track_info = render_soundcloud_search(remove_free_dl(handler.file.stem))

    c1, c2 = st.columns((2, 8))
    with c1:
        st.subheader(":material/description: Edit Track Metadata")
        render_auto_checkboxes(handler, sc_track_info)
    modified_info = modify_track_info(handler.track_info, has_artwork=bool(handler.covers), sc_track_info=sc_track_info)
    with c2.container(border=True):
        cc1, cc2 = st.columns((1, 9))
        cc2.caption(f"_Generated Filename:_ `{modified_info.filename}`")
        if cc1.button(":material/save:", help="Save Metadata", use_container_width=True, key="save_file"):
            handler.add_info(modified_info, artwork=modified_info.artwork)
            sst.new_track_name = handler.rename(modified_info.filename)
            st.success("Saved Successfully")
            st.rerun()
        render_track_info(handler.track_info)

    with st.expander("Cover Handler"):
        cover_handler(handler.track, artwork=modified_info.artwork)

    with st.expander("Tags"):
        for tag in handler.track.tags:
            st.write(tag, handler.track.tags[tag])


def copy_track_info(track_info: TrackInfo):
    sst.ti_title = track_info.title
    sst.ti_artist = track_info.artist_str
    sst.ti_genre = track_info.genre
    sst.ti_year = track_info.year
    sst.ti_release_date = track_info.release_date


def copy_artwork(artwork_url: str):
    sst.ti_artwork_url = artwork_url


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


def render_soundcloud_search(query: str, autocopy: bool = False) -> TrackInfo | None:
    st.write("__:material/cloud: Soundcloud Search__")
    query = st.text_input("Search", query)
    sst.setdefault("search_result", {})
    sst.search_result[query] = asyncio.run(get_client().search(q=query))
    if not (result := sst.search_result.get(query)):
        return None

    st.divider()
    track_ph = st.container(border=True)

    tracks: list[Track] = [track for track in result.collection if track.kind == "track"]
    if not tracks:
        st.warning("No tracks found")
        return None

    track = st.radio("Tracks", tracks, format_func=lambda t: f"[{t.title} - {t.user.username}]({t.permalink_url})")

    st.divider()

    track_info = TrackInfo.from_sc_track(track)
    with track_ph:
        render_embedded_track(track)
        c1, c2 = st.columns(2)
        c1.button(
            ":material/cloud_download:",
            help="Copy Metadata from Soundcloud",
            use_container_width=True,
            on_click=copy_track_info,
            args=(track_info,),
        )
        c2.button(
            ":material/library_music:",
            help="Copy Artwork from Soundcloud",
            use_container_width=True,
            on_click=copy_artwork,
            args=(track_info.artwork_url,),
        )
    with st.expander("Track Metadata"):
        st.write(track)
    return track_info


def remove_free_dl(title: str):
    return re.sub(r"[\(\[\{]\s*free\s*(dl|download)\s*.*?[\)\]\}]", "", title, flags=re.IGNORECASE)


def clean_title(title: str):
    title = remove_free_dl(title)
    if "(" in title:
        return title.strip()
    first_dash = title.find("- ")
    if first_dash == -1:
        return title.strip()
    return title[first_dash + 1 :].strip()


def clean_artists(artists: str) -> str:
    for seq in {" & ", " and ", " x ", " X "}:
        artists = artists.replace(seq, ", ")
    return artists


def titelize(string: str) -> str:
    return string.title().replace("Dj", "DJ")


def changed_string(old: str, new: str) -> bool:
    return " ⚠️ " if old != new else ""


def render_auto_checkboxes(handler: TrackHandler, sc_track_info: TrackInfo):
    if st.checkbox(
        ":material/cleaning_services: Auto-Clean",
        value=False,
        key="auto_clean",
        help=(
            "Automatically cleanup Title and Artists "
            "(Removes Free DL mentions, artists in title and separates artists into a list)"
        ),
    ):
        apply_to_sst(clean_title, "ti_title")()
        apply_to_sst(clean_artists, "ti_artist")()
    if st.checkbox(
        ":material/arrow_upward: Auto-Titelize",
        value=False,
        key="auto_titelize",
        help="Automatically titelizes Artists and Title",
    ):
        apply_to_sst(titelize, "ti_title")()
        apply_to_sst(titelize, "ti_artist")()
    if st.checkbox(
        ":material/add_photo_alternate: Auto-Copy Artwork",
        value=False,
        key="auto_copy_artwork",
        help="Automatically copy artwork if not present",
    ):
        if not handler.track_info.artwork and sc_track_info:
            copy_artwork(sc_track_info.artwork_url)
    cols = st.columns(3)
    cols[0].button(
        ":material/cloud_download:",
        help="Copy complete metadata from Soundcloud",
        key="copy_metadata",
        on_click=copy_track_info,
        args=(sc_track_info,),
        disabled=sc_track_info is None,
        use_container_width=True,
    )
    with cols[1]:
        if st.button(":material/delete:", key="del_outer", help="Delete file", use_container_width=True):
            delete_file(handler)

    if handler.track_info.filename != handler.file.stem:
        if st.button(
            "Rename File",
            key="rename",
            use_container_width=True,
            help=f"Filename does not match track info, rename to '{handler.track_info.filename}'",
        ):
            st.success("Renamed Successfully")
            sst.new_track_name = handler.rename(handler.track_info.filename)
            st.rerun()

    if handler.mp3_file.exists():
        st.warning("File already exists in export folder")
    if cols[2].button(
        ":material/done_all:",
        help=(
            f"Track has {len(handler.covers)} covers, "
            f"Metadata {'' if handler.track_info.complete else 'not '}complete.\n"
            "Export to 320kb/s mp3 file."
        ),
        disabled=len(handler.covers) != 1 or not handler.track_info.complete,
        use_container_width=True,
    ):
        with st.spinner("Finalizing"):
            match handler.file.suffix:
                case ".mp3":
                    handler.move_to_cleaned()
                case _:
                    handler.convert_to_mp3()
                    handler.add_mp3_info()
                    handler.archive()

        st.success("Finalized Successfully")
        reset_track_info_sst()
        st.rerun()


def bold(text: str) -> str:
    return f"__{text}__" if text else text


def modify_track_info(
    track_info: TrackInfo,
    sc_track_info: TrackInfo | None,
    has_artwork: bool = False,
) -> TrackInfo:
    title_col, artist_col, dates_col = st.columns((4, 4, 2))
    # Title
    with title_col.container(border=True):
        c1, c2 = st.columns((1, 9))
        c2.write(f"__Title__{changed_string(track_info.title, sst.ti_title)}")
        c2.caption(f"Old {bold(track_info.title) or '`None`'}")
        c1.button(
            ":material/cloud_download:",
            help="Copy Metadata from Soundcloud",
            on_click=sst.__setitem__,
            args=("ti_title", sc_track_info and sc_track_info.title),
            use_container_width=True,
            key="copy_title",
            disabled=sc_track_info is None,
        )
        title = c2.text_input(
            "Title",
            track_info.title,
            key="ti_title",
            label_visibility="collapsed",
        )
        c1.button(
            ":material/cleaning_services:",
            help="Clean",
            key="clean_title",
            on_click=apply_to_sst(clean_title, "ti_title"),
            use_container_width=True,
        )
        c1.button(
            ":material/arrow_upward:",
            help="Titelize",
            key="titelize_title",
            on_click=apply_to_sst(titelize, "ti_title"),
            use_container_width=True,
        )

    # Artists
    with artist_col.container(border=True):
        c1, c2 = st.columns((1, 9))
        c2.write(f"__Artists__{changed_string(track_info.artist_str, sst.ti_artist)}")
        c2.caption(f"Old {bold(track_info.artist_str) or '`None`'}")
        c1.button(
            ":material/cloud_download:",
            help="Copy Metadata from Soundcloud",
            on_click=sst.__setitem__,
            args=("ti_artist", sc_track_info and sc_track_info.artist_str),
            use_container_width=True,
            key="copy_artists",
            disabled=sc_track_info is None,
        )
        artist = c2.text_input(
            "Artist",
            track_info.artist_str,
            key="ti_artist",
            label_visibility="collapsed",
        )
        c1.button(
            ":material/cleaning_services:",
            help="Clean",
            key="clean_artist",
            on_click=apply_to_sst(clean_artists, "ti_artist"),
            use_container_width=True,
        )
        c1.button(
            ":material/arrow_upward:",
            help="Titelize",
            key="titelize_artist",
            on_click=apply_to_sst(titelize, "ti_artist"),
            use_container_width=True,
        )

        artists = [a.strip() for a in artist.split(",")]
        if len(artists) == 1:
            artists = artists[0]
        c2.caption(f"Parsed: __{artists}__" if artists else "No Artists")

    artwork_col, genre_col = st.columns(2)

    # Artwork
    with artwork_col.container(border=True):
        c1, c2 = st.columns((1, 9))
        c2.write("__Artwork__")
        c1.button(
            ":material/cloud_download:",
            key="copy_artwork_sc",
            on_click=copy_artwork,
            args=(sc_track_info and sc_track_info.artwork_url,),
            use_container_width=True,
            disabled=sc_track_info is None,
        )
        c1.button(
            ":material/delete:",
            key="delete_artwork",
            on_click=sst.__setitem__,
            args=("ti_artwork_url", ""),
            use_container_width=True,
        )
        artwork_url = c2.text_input("URL", track_info.artwork_url, key="ti_artwork_url")
        if has_artwork:
            c2.warning("Track already has artwork, no need to copy.")
        if not has_artwork and not artwork_url:
            c2.error("Current track has no artwork, you should copy it.")
        if artwork_url:
            c1.image(artwork_url, width=ARTWORK_WIDTH)

    # Genre
    with genre_col.container(border=True):
        st.write(f"__Genre__{changed_string(track_info.genre, sst.ti_genre)}")
        gcols = st.columns(3)
        genres = ["Trance", "Hardtrance", "House"]
        for i, genre in enumerate(genres):
            if gcols[i].button(genre, use_container_width=True):
                sst.ti_genre = genre
        genre = st.text_input("Genre", track_info.genre, key="ti_genre", label_visibility="collapsed")

    # Dates
    with dates_col.container(border=True):
        c1, c2 = st.columns((1, 9))
        c2.write("__Dates__")
        c1.button(
            ":material/cloud_download:",
            key="copy_dates_sc",
            on_click=lambda date, year: (
                sst.__setitem__("ti_release_date", date),
                sst.__setitem__("ti_year", year),
            ),
            args=(sc_track_info and sc_track_info.release_date, sc_track_info and sc_track_info.year),
            use_container_width=True,
            disabled=sc_track_info is None,
        )
        year = st.number_input(
            f"Year{changed_string(track_info.year, sst.ti_year)}",
            track_info.year,
            key="ti_year",
        )
        release_date = st.text_input(
            f"Release Date{changed_string(track_info.release_date, sst.ti_release_date)}",
            track_info.release_date,
            key="ti_release_date",
        )

    return TrackInfo(
        title=title,
        artist=artists,
        genre=genre,
        year=year,
        release_date=release_date,
        artwork_url=artwork_url,
    )


def preparte_table_data(data: dict):
    data = [("<b>" + k.replace("_", " ").title() + "</b>", v or "⚠️") for k, v in data.items()]
    table(data)


def render_track_info(track_info: TrackInfo, vertical: bool = False):
    st.write("__Metadata__")
    c1, c2, c3 = (st.container(), st.container(), st.container()) if vertical else st.columns(3)
    with c1:
        table(preparte_table_data(track_info.model_dump(include={"title", "artist", "genre"})))
    with c2:
        table(preparte_table_data(track_info.model_dump(include={"release_date", "year"})))
    with c3:
        st.write("__Artwork__")
        if track_info.artwork:
            st.image(track_info.artwork, width=ARTWORK_WIDTH)
            st.caption(track_info.artwork_url)
        else:
            st.error("No Artwork")


def cover_handler(track: ID3FileType, artwork: bytes | None = None):
    c1, c2 = st.columns(2)
    c1.write("__Artwork__")

    if covers := track.tags.getall("APIC"):
        c2.write(f"Track has {len(covers)} covers")
    else:
        c2.error("Track has no covers")

    all_covers = copy(covers)
    for i, cover in enumerate(covers):
        c1, c2 = st.columns((1, 2))
        c1.image(cover.data, caption=f"Cover {i}", width=ARTWORK_WIDTH)
        file_name = f"{track.tags.get("TPE1", "")}-{track.tags.get("TPE1", "")}_cover_{i}.jpg"
        c2.download_button(f":material/download: {i}", data=cover.data, file_name=file_name, key=file_name)
        if c2.button(":material/delete:", key=f"remove_{i}_{bool(artwork)}"):
            all_covers.pop(i)
            track.tags.setall("APIC", all_covers)
            st.rerun()

    st.divider()
    c1, c2, c3 = st.columns(3)
    if c2.button(":material/delete:", key=f"remove_all_{bool(artwork)}", use_container_width=True):
        track.tags.delall("APIC")
        track.save()
        st.success("Covers removed")
    if artwork and c1.button(":material/add:", key=f"{bool(artwork)}", use_container_width=True):
        track.tags.add(
            APIC(
                encoding=0,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=artwork,
            )
        )
        track.save()
        st.success("Artwork added")
    c3.button(":material/refresh:", key=f"reload_{bool(artwork)}", use_container_width=True)


def file_selector() -> tuple[Path, Path]:
    c1, c2 = st.columns((4, 1))

    with c1:
        root_folder = st.text_input("Root folder", value="~/Music/tracks")
        try:
            root_folder = Path(root_folder).expanduser()
            assert root_folder.exists()
        except (AssertionError, FileNotFoundError):
            st.error("Invalid root folder")
            st.stop()

        direct = st.checkbox("Direct", key="direct", help="Iterate through root folder directly")
        path = root_folder / "prepare" if not direct else root_folder

        if not (files := load_tracks(path)):
            st.error("No files found")
            st.stop()
    with c2:
        st.write("__Files__")
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
    )
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
    )

    if "new_track_name" in sst:
        sst.index = files.index(sst.new_track_name)
        if sst.index >= len(files):
            sst.index = 0
        del sst.new_track_name

    selected_file = files[sst.index]
    return selected_file, root_folder


def main():
    st.header(":material/database: MetaEditor")
    st.write("Edit track metadata with integrated Soundcloud search and export to 320kb/s mp3 files.")
    st.divider()
    with st.sidebar:
        st.subheader(":material/folder: Folder Selection")
        file, root_folder = file_selector()
        st.divider()
    render_file(file, root_folder)


if __name__ == "__main__":
    main()

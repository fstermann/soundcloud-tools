import streamlit as st
from streamlit import session_state as sst

from soundcloud_tools.handler.track import Comment, Remix, TrackInfo
from soundcloud_tools.predict.base import Predictor
from soundcloud_tools.predict.bpm import BPMPredictor
from soundcloud_tools.predict.style import StylePredictor
from soundcloud_tools.streamlit.utils import apply_to_sst
from soundcloud_tools.utils.string import (
    bold,
    changed_string,
    clean_artists,
    clean_title,
    get_raw_title,
    is_remix,
    remove_parenthesis,
    titelize,
)

ARTWORK_WIDTH = 100


def build_button_columns(n_buttons: int, left: float = 0.2):
    return st.columns([left] + [(1 - left) / n_buttons] * n_buttons)


def build_title_from_remix(title: str):
    return f"{sst.ti_original_artist} - {get_raw_title(title)} ({sst.ti_remixer} {sst.ti_mix_name})"


def title_editor(track_info: TrackInfo, sc_track_info: TrackInfo | None) -> str:
    cols = iter(build_button_columns(5))
    sst.setdefault("ti_title", track_info.title)
    next(cols).write(f"__Title__{changed_string(track_info.title, sst.ti_title)}")
    next(cols).button(
        ":material/cloud_download:",
        help="Copy Metadata from Soundcloud",
        on_click=sst.__setitem__,
        args=("ti_title", sc_track_info and sc_track_info.title),
        use_container_width=True,
        key="copy_title",
        disabled=sc_track_info is None,
    )
    next(cols).button(
        ":material/cleaning_services:",
        help="Clean",
        key="clean_title",
        on_click=apply_to_sst(clean_title, "ti_title"),
        use_container_width=True,
    )
    next(cols).button(
        ":material/tune:",
        help="Build from Remix data",
        key="build_title",
        on_click=apply_to_sst(build_title_from_remix, "ti_title"),
        use_container_width=True,
    )
    next(cols).button(
        ":material/arrow_upward:",
        help="Titelize",
        key="titelize_title",
        on_click=apply_to_sst(titelize, "ti_title"),
        use_container_width=True,
    )
    next(cols).button(
        ":material/data_array:",
        help="Remove `[]` parenthesis",
        key="remove_parenthesis_title",
        on_click=apply_to_sst(remove_parenthesis, "ti_title"),
        use_container_width=True,
    )
    title = st.text_input("Title", key="ti_title", label_visibility="collapsed")
    st.caption(f"Old: {bold(track_info.title) or '`None`'}")
    return title


def render_artist_options(artist_options: set[str], key: str, label: str | None = None, disabled: bool = False):
    with st.popover(f":material/groups: {label or ''}", use_container_width=True, disabled=disabled):
        if artist := sst.get(key):
            artist_options |= {artist}
        for artist in artist_options:
            st.button(artist, key=f"artist_option_{key}_{artist}", on_click=sst.__setitem__, args=(key, artist))


def artist_editor(track_info: TrackInfo, sc_track_info: TrackInfo | None) -> str | list[str]:
    cols = iter(build_button_columns(4))
    sst.setdefault("ti_artist", track_info.artist_str)
    next(cols).write(f"__Artists__{changed_string(track_info.artist_str, sst.ti_artist)}")
    next(cols).button(
        ":material/cloud_download:",
        help="Copy Metadata from Soundcloud",
        on_click=sst.__setitem__,
        args=("ti_artist", sc_track_info and sc_track_info.artist_str),
        use_container_width=True,
        key="copy_artists",
        disabled=sc_track_info is None,
    )
    next(cols).button(
        ":material/cleaning_services:",
        help="Clean",
        key="clean_artist",
        on_click=apply_to_sst(clean_artists, "ti_artist"),
        use_container_width=True,
    )
    next(cols).button(
        ":material/arrow_upward:",
        help="Titelize",
        key="titelize_artist",
        on_click=apply_to_sst(titelize, "ti_artist"),
        use_container_width=True,
    )
    with next(cols):
        render_artist_options(sc_track_info.artist_options if sc_track_info else set(), key="ti_artist")

    artist = st.text_input("Artist", key="ti_artist", label_visibility="collapsed")
    artists = [a.strip() for a in artist.split(",")]
    if len(artists) == 1:
        artists = artists[0]
    st.caption(f"Old: {bold(track_info.artist_str) or '`None`'} | Parsed: __{artists}__" if artists else "No Artists")
    return artists


def artwork_editor(track_info: TrackInfo, sc_track_info: TrackInfo | None, has_artwork: bool = False):
    c1, c2 = st.columns((1, 9))
    cols = iter(build_button_columns(2))
    next(cols).write("__Artwork__")
    next(cols).button(
        ":material/cloud_download:",
        key="copy_artwork_sc",
        on_click=sst.__setitem__,
        args=("ti_artwork_url", sc_track_info and sc_track_info.artwork_url),
        use_container_width=True,
        disabled=sc_track_info is None,
    )
    next(cols).button(
        ":material/delete:",
        key="delete_artwork",
        on_click=sst.__setitem__,
        args=("ti_artwork_url", ""),
        use_container_width=True,
        disabled=not has_artwork,
    )
    sst.setdefault("ti_artwork_url", track_info.artwork_url)
    c1, c2 = st.columns((8, 2))
    artwork_url = c1.text_input("URL", key="ti_artwork_url", label_visibility="collapsed")

    help_str = ""
    if has_artwork:
        help_str += "Track already has artwork, no need to copy. "
    if not has_artwork and not artwork_url:
        help_str += "Current track has no artwork, you should copy it."
    if help_str:
        c1.caption(help_str)
    if artwork_url:
        c2.image(artwork_url, width=ARTWORK_WIDTH)
    return artwork_url


def render_predictor(predictor: Predictor, filename: str, autopredict: bool = False):
    key = predictor.__class__.__name__
    if autopredict:
        if (pred := sst.get((filename, key))) is not None:
            return pred
        sst[(filename, key)] = predictor.predict(filename)
        return sst[(filename, key)]
    if st.button(f"Predict {predictor.title}", key=f"predict-{key}", help=predictor.help):
        sst[(filename, key)] = predictor.predict(filename)
    return sst.get((filename, key))


def genre_editor(track_info: TrackInfo, sc_track_info: TrackInfo | None, filename: str) -> str:
    c1, c2, c3, c4 = st.columns((1.5, 6.5, 1, 1))
    c1.write(f"__Genre__{changed_string(track_info.genre, sst.get("ti_genre"))}")
    if c2.toggle("Predict"):
        genres = render_predictor(StylePredictor(), filename, autopredict=True)
        bpm = render_predictor(BPMPredictor(), filename, autopredict=True)
        c3.write(f"BPM __{bpm}__")
    else:
        genres = [("Trance", ""), ("Hardtrance", ""), ("House", "")]

    gcols = st.columns(len(genres) + 1)
    for i, (genre, prob) in enumerate(genres, start=1):
        prob_str = prob and f" ({prob:.2f})"
        if gcols[i].button(f"{genre}{prob_str}", use_container_width=True):
            sst.ti_genre = genre

    sst.setdefault("ti_genre", track_info.genre)
    c4.button(
        ":material/cloud_download:",
        key="copy_genre_sc",
        on_click=sst.__setitem__,
        args=("ti_genre", sc_track_info and sc_track_info.genre),
        use_container_width=True,
        disabled=sc_track_info is None,
    )

    genre = gcols[0].text_input("Genre", key="ti_genre", label_visibility="collapsed")
    return genre


def dates_editor(track_info: TrackInfo, sc_track_info: TrackInfo | None):
    cols = iter(st.columns(2))
    next(cols).write("__Dates__")
    next(cols).button(
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
    sst.setdefault("ti_year", track_info.year)

    c1, c2 = st.columns(2)
    year = c1.number_input(f"Year{changed_string(track_info.year, sst.get("ti_year"))}", key="ti_year", step=1)
    sst.setdefault("ti_release_date", track_info.release_date)
    release_date = c2.text_input(
        f"Release Date{changed_string(track_info.release_date, sst.get("ti_release_date"))}", key="ti_release_date"
    )
    return year, release_date


def remix_editor(track_info: TrackInfo, sc_track_info: TrackInfo | None) -> Remix | None:
    c0, c1, c2, c3 = st.columns((1, 3, 3, 3))
    sst.setdefault("ti_is_remix", track_info.remix or is_remix(track_info.title) if track_info else False)
    if remix := c0.checkbox("__RMX__", key="ti_is_remix"):
        sst.setdefault("ti_remixer", (track_info.remix and track_info.remix.remixer_str) or "")
        sst.setdefault("ti_original_artist", track_info.remix and track_info.remix.original_artist_str)
        sst.setdefault("ti_mix_name", track_info.remix and track_info.remix.mix_name)

    remixer = c1.text_input("Remixer", key="ti_remixer", disabled=not remix)
    original_artist = c2.text_input("Original Artist", key="ti_original_artist", disabled=not remix)
    mix_name = c3.text_input("Mix Name", key="ti_mix_name", disabled=not remix)

    c_copy, *cols = st.columns((1, 1.5, 1.5, 1.5, 1.5, 3))
    remix_ = sc_track_info and sc_track_info.remix

    c_copy.button(
        ":material/cloud_download:",
        key="copy_remix_sc",
        on_click=lambda remixer, original_artist, mix_name: (
            sst.__setitem__("ti_remixer", remixer),
            sst.__setitem__("ti_original_artist", original_artist),
            sst.__setitem__("ti_mix_name", mix_name),
        ),
        args=(
            remix_ and remix_.remixer_str,
            remix_ and remix_.original_artist_str,
            remix_ and remix_.mix_name,
        ),
        use_container_width=True,
        disabled=(not remix) or remix_ is None,
    )

    # Remixer
    with cols[0]:
        render_artist_options(
            sc_track_info.artist_options if sc_track_info else set(),
            key="ti_remixer",
            disabled=not remix,
        )
    cols[1].button(
        ":material/arrow_upward:",
        help="Titelize",
        key="titelize_remixer",
        on_click=apply_to_sst(titelize, "ti_remixer"),
        use_container_width=True,
        disabled=not remix,
    )
    # Original Artist
    with cols[2]:
        render_artist_options(
            sc_track_info.artist_options if sc_track_info else set(),
            key="ti_original_artist",
            disabled=not remix,
        )
    cols[3].button(
        ":material/arrow_upward:",
        help="Titelize",
        key="titelize_original_artist",
        on_click=apply_to_sst(titelize, "ti_original_artist"),
        use_container_width=True,
        disabled=not remix,
    )

    # Mix Name
    cols[4].button(
        ":material/arrow_upward:",
        help="Titelize",
        key="titelize_mix_name",
        on_click=apply_to_sst(titelize, "ti_mix_name"),
        use_container_width=True,
        disabled=not remix,
    )

    if not remix:
        return None
    return Remix(remixer=remixer, original_artist=original_artist, mix_name=mix_name)


def comment_editor(track_info: TrackInfo, sc_track_info: TrackInfo | None) -> Comment | None:
    cols = iter(st.columns(2))
    sst.setdefault("ti_comment", track_info.comment.to_str() if track_info and track_info.comment else "")
    comment = sst.get("ti_comment")
    old_comment = track_info.comment.to_str() if track_info and track_info.comment else ""
    next(cols).write(f"__Comment__ {changed_string(old_comment, comment)}")
    next(cols).button(
        ":material/cloud_download:",
        key="copy_comments_sc",
        on_click=sst.__setitem__,
        args=("ti_comment", sc_track_info and sc_track_info.comment and sc_track_info.comment.to_str()),
        use_container_width=True,
        disabled=sc_track_info is None,
    )
    if not comment:
        return None
    st.code(comment.replace("\n", "  \n"))
    return Comment.from_str(comment)

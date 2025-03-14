import logging
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from soundcloud_tools.handler.track import TrackHandler
from soundcloud_tools.predict.style import StylePredictor
from soundcloud_tools.utils import load_tracks

logger = logging.getLogger(__name__)

# with st.sidebar.container(border=True):
#     st.caption("__Settings__")
#     show_collection_ops = st.toggle("Show Collection Operations")

# st.subheader(":material/folder: Folder Selection")
# file, root_folder = file_selector()
# if file is None:
#     st.warning("No files present in folder")
#     return


# if show_collection_ops:
#     render_collection_operations(file, root_folder)
@st.cache_data
def load_track_infos(folder: Path):
    return [t.track_info for t in TrackHandler.load_all(folder)]


def render_collection_operations(file: Path, root_folder: Path):
    with st.container(border=True):
        data_folder = file.parent
        st.write(data_folder)
        render_genre_chart(data_folder)
        render_artist_chart(data_folder)
        files = load_tracks(data_folder)
        all_genres = []
        chart_ph = st.empty()
        if st.button(f"Autodetect Genres ({len(files)})"):
            predictor = StylePredictor(max_classes=1)
            pbar = st.progress(0, "Autodetecting genres")
            for i, file in enumerate(files, start=1):
                handler = TrackHandler(root_folder=root_folder, file=file)
                genre, prob = predictor.predict(str(handler.file))[0]
                prog = round(i * 100 / len(files))
                prog_text = (
                    f"{i}/{len(files)} | "
                    f"Predicted genre: __{genre}__ with prob: {prob:.2f} for track `{handler.file.stem}`"
                )
                logger.info(prog_text)
                pbar.progress(prog, prog_text)
                handler.set_genre(genre)

                all_genres.append(genre)
                chart_ph.bar_chart(pd.DataFrame.from_dict(Counter(all_genres), orient="index"))
            st.success("Autodetected genres")


def render_genre_chart(folder: Path):
    infos = load_track_infos(folder)
    genres = [info.genre for info in infos]
    data = pd.DataFrame.from_dict(Counter(genres), orient="index").sort_values(by=0, ascending=False)
    sel = st.plotly_chart(px.bar(data), on_select="rerun")
    indices = sel["selection"]["point_indices"]
    selected_genres = data.index[indices].tolist()
    st.write(selected_genres)
    selected_data = pd.DataFrame(
        [info.model_dump(exclude={"artwork"}) for info in infos if info.genre in selected_genres]
    )
    st.dataframe(selected_data)


def render_artist_chart(folder: Path):
    infos = load_track_infos(folder)
    artst_genre = [
        (artist, info.genre)
        for info in infos
        for artist in (info.artist if isinstance(info.artist, list) else [info.artist])
    ]
    artists = {
        artist: Counter([genre for a, genre in artst_genre if a == artist]) for artist in {a for a, _ in artst_genre}
    }
    # data = pd.DataFrame(artst_genre, columns=["artist", "genre"])
    st.write(len(artists), "Artists in the collection")
    # sel = st.plotly_chart(px.bar(data, x="artist", color="genre"), on_select="rerun")

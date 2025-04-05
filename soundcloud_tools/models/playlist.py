import logging
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from soundcloud_tools.models.track import Track, TrackID, TrackSlim
from soundcloud_tools.models.user import User

logger = logging.getLogger(__name__)


class PlaylistCreate(BaseModel):
    title: str
    description: str
    sharing: Literal["public", "private"] = "private"
    tracks: list[TrackID] = []
    tag_list: str = ""

    @field_validator("tracks", mode="before")
    def validate_tracks(cls, tracks: list[TrackID]):
        if not tracks:
            raise ValueError("At least one track is required for the playlist")
        if len(tracks) > 500:
            logger.warning("Playlist has more than 500 tracks, truncating track list")
            tracks = tracks[:500]
        return tracks


class PlaylistUpdateImageRequest(BaseModel):
    image_data: str


class PlaylistUpdateImageResponse(BaseModel):
    artwork_url: str


class Playlist(BaseModel):
    artwork_url: str | None
    created_at: datetime
    description: str | None = None
    duration: int
    embeddable_by: str | None = None
    genre: str | None = None
    id: int
    kind: Literal["playlist"]
    label_name: str | None = None
    last_modified: datetime
    license: str | None = None
    likes_count: int | None = None
    managed_by_feeds: bool
    permalink: str
    permalink_url: str
    public: bool
    purchase_title: str | None = None
    purchase_url: str | None = None
    release_date: str | None
    reposts_count: int | None = None
    secret_token: str | None
    sharing: str
    tag_list: str | None = None
    title: str
    uri: str
    user_id: int
    set_type: str
    is_album: bool
    published_at: str | None
    display_date: datetime
    user: User
    tracks: list[Track | TrackSlim] = []
    track_count: int

    @property
    def hq_artwork_url(self) -> str | None:
        return self.artwork_url and self.artwork_url.replace("-large.", "-t500x500.")


class Seed(BaseModel):
    urn: str
    permalink: str


class SystemPlaylist(BaseModel):
    urn: str
    query_urn: str | None
    permalink: str
    permalink_url: str
    title: str
    description: str
    short_title: str
    short_description: str
    tracking_feature_name: str
    playlist_type: str
    last_updated: str | None
    artwork_url: str
    calculated_artwork_url: str
    likes_count: int
    seed: Seed | None = None
    tracks: list[TrackSlim]
    is_public: bool
    made_for: User | None
    user: User
    kind: Literal["system-playlist"]
    id: str


class UserPlaylistBaseItem(BaseModel):
    created_at: datetime
    type: str
    user: User
    uuid: str
    caption: str | None = None


class UserPlaylistItem(UserPlaylistBaseItem):
    playlist: Playlist
    type: Literal["playlist"]


class UserPlaylistLikeItem(UserPlaylistBaseItem):
    playlist: Playlist
    type: Literal["playlist-like"]


class UserSystemPlaylistLikeItem(UserPlaylistBaseItem):
    system_playlist: SystemPlaylist
    type: Literal["system-playlist-like"]


PlaylistItem = Annotated[
    Playlist | SystemPlaylist,
    # UserPlaylistItem | UserPlaylistLikeItem | UserSystemPlaylistLikeItem,
    Field(discriminator="kind"),
]


class UserPlaylists(BaseModel):
    collection: list[PlaylistItem]
    next_href: str | None
    query_urn: str | None

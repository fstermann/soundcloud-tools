from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from soundcloud_tools.models.track import Track, TrackID, TrackSlim
from soundcloud_tools.models.user import User


class PlaylistCreate(BaseModel):
    title: str
    description: str
    sharing: Literal["public", "private"] = "private"
    tracks: list[TrackID] = []
    tag_list: str = ""


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
    likes_count: int
    managed_by_feeds: bool
    permalink: str
    permalink_url: str
    public: bool
    purchase_title: str | None = None
    purchase_url: str | None = None
    release_date: str | None
    reposts_count: int
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

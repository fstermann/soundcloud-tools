from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from soundcloud_archive.models.playlist import Playlist
from soundcloud_archive.models.track import Track
from soundcloud_archive.models.user import User


class BaseItem(BaseModel):
    created_at: datetime
    type: str
    user: User
    uuid: str
    caption: str | None = None


class Reposted(BaseModel):
    target_urn: str
    user_urn: str
    caption: str | None


class BaseRepostItem(BaseItem):
    reposted: Reposted | None = None


class TrackStreamItem(BaseItem):
    type: Literal["track"]
    track: Track


class TrackStreamRepostItem(BaseRepostItem):
    type: Literal["track-repost"]
    track: Track


class PlaylistStreamItem(BaseItem):
    type: Literal["playlist"]
    playlist: Playlist


class PlaylistStreamRepostItem(BaseRepostItem):
    type: Literal["playlist-repost"]
    playlist: Playlist


StreamItem = Annotated[
    TrackStreamItem | TrackStreamRepostItem | PlaylistStreamItem | PlaylistStreamRepostItem,
    Field(discriminator="type"),
]
StreamItemType = Literal["track", "track-repost", "playlist", "playlist-repost"]


class Stream(BaseModel):
    collection: list[StreamItem]
    next_href: str | None
    query_urn: str | None

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from soundcloud_tools.models.playlist import Playlist
from soundcloud_tools.models.track import Track


class BaseLike(BaseModel):
    created_at: datetime
    kind: Literal["like"]


class TrackLike(BaseLike):
    track: Track


class PlaylistLike(BaseLike):
    playlist: Playlist


Like = TrackLike | PlaylistLike


class Likes(BaseModel):
    collection: list[Like]
    next_href: str | None = None
    query_urn: str | None = None

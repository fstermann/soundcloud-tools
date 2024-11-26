from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from soundcloud_tools.models.track import TrackSlim
from soundcloud_tools.models.user import User


class CommentSelf(BaseModel):
    urn: str


class Comment(BaseModel):
    id: int
    kind: Literal["comment"]
    type: Literal["comment"] = "comment"  # Auxillary field
    body: str
    created_at: datetime
    timestamp: int
    track_id: int
    user_id: int
    self: CommentSelf
    user: User
    track: TrackSlim


class Comments(BaseModel):
    collection: list[Comment]
    next_href: str | None
    query_urn: str | None

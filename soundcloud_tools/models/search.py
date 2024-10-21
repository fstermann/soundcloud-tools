from typing import Annotated

from pydantic import BaseModel, Field
from soundcloud_tools.models.playlist import Playlist
from soundcloud_tools.models.track import Track
from soundcloud_tools.models.user import User

SearchItem = Annotated[Playlist | Track | User, Field(discriminator="kind")]


class Search(BaseModel):
    collection: list[SearchItem]
    next_href: str | None = None
    query_urn: str | None = None
    total_results: int

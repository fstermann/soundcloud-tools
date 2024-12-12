from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from soundcloud_tools.models.playlist import Playlist
from soundcloud_tools.models.track import Track, TrackSlim
from soundcloud_tools.models.user import User


class ArtistShortcut(BaseModel):
    user_urn: str
    unread_update_at: datetime | None = None
    has_read: bool = False
    user: User


class ArtistShortcuts(BaseModel):
    collection: list[ArtistShortcut]


class BaseStory(BaseModel):
    created_at: datetime
    target_urn: str
    type: str


class Reposted(BaseModel):
    target_urn: str
    user_urn: str
    caption: str | None


class TrackPostStory(BaseStory):
    type: Literal["track-post"]
    snippeted_track: Track | TrackSlim


class PlaylistPostStory(BaseStory):
    type: Literal["playlist-post"]
    snippeted_track: Track | TrackSlim
    playlist: Playlist


class TrackRepostStory(BaseStory):
    type: Literal["track-repost"]
    snippeted_track: Track | TrackSlim
    reposted: Reposted | None = None


class PlaylistRepostStory(BaseStory):
    type: Literal["playlist-repost"]
    snippeted_track: Track | TrackSlim
    playlist: Playlist
    reposted: Reposted | None = None


Story = Annotated[
    TrackPostStory | PlaylistPostStory | TrackRepostStory | PlaylistRepostStory,
    Field(discriminator="type"),
]
StoryType = Literal["track-post", "track-repost", "playlist-post", "playlist-repost"]


class ArtistShortcutStories(BaseModel):
    artist_urn: str
    last_read_story_timestamp: datetime | None = None
    stories: list[Story]

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

type TrackID = int


class PlaylistCreate(BaseModel):
    title: str
    description: str
    sharing: Literal["public", "private"] = "private"
    tracks: list[TrackID] = []
    tag_list: str


class CreatePlaylist(BaseModel):
    playlist: PlaylistCreate


class Badges(BaseModel):
    pro: bool
    creator_mid_tier: bool
    pro_unlimited: bool
    verified: bool


class User(BaseModel):
    avatar_url: str
    first_name: str
    followers_count: int
    full_name: str
    id: int
    kind: Literal["user"]
    last_modified: datetime
    last_name: str
    permalink: str
    permalink_url: str
    uri: str
    urn: str
    username: str
    verified: bool
    city: str | None
    country_code: str | None
    badges: Badges
    station_urn: str
    station_permalink: str


class PublisherMetadata(BaseModel):
    id: int
    urn: str

    contains_music: bool | None = None
    artist: str | None = None
    isrc: str | None = None
    explicit: bool | None = None
    writer_composer: str | None = None


class Format(BaseModel):
    protocol: str
    mime_type: str


class Transcoding(BaseModel):
    url: str
    preset: str
    duration: int
    snipped: bool
    format: Format
    quality: str


class Media(BaseModel):
    transcodings: list[Transcoding]


class Visual(BaseModel):
    urn: str
    entry_time: int
    visual_url: str


class Visuals(BaseModel):
    urn: str
    enabled: bool
    visuals: list[Visual]
    tracking: Any | None


class TrackSlim(BaseModel):
    id: int
    kind: str
    monetization_model: str
    policy: str


class Track(BaseModel):
    artwork_url: str | None
    caption: str | None
    commentable: bool
    comment_count: int | None
    created_at: datetime
    description: str | None
    downloadable: bool
    download_count: int | None
    duration: int
    full_duration: int
    embeddable_by: str
    genre: str | None = None
    has_downloads_left: bool
    id: int
    kind: Literal["track"]
    label_name: str | None
    last_modified: datetime
    license: str
    likes_count: int | None
    permalink: str
    permalink_url: str
    playback_count: int | None
    public: bool
    publisher_metadata: PublisherMetadata | None
    purchase_title: str | None
    purchase_url: str | None
    release_date: str | None
    reposts_count: int
    secret_token: str | None
    sharing: str
    state: str
    streamable: bool
    tag_list: str
    title: str
    uri: str
    urn: str
    user_id: int
    visuals: Visuals | None
    waveform_url: str
    display_date: datetime
    media: Media
    station_urn: str
    station_permalink: str
    track_authorization: str
    monetization_model: str
    policy: str
    user: User

    @property
    def hq_artwork_url(self) -> str:
        return self.artwork_url.replace("-large.", "-t500x500.")


class Playlist(BaseModel):
    artwork_url: str | None
    created_at: datetime
    description: str | None
    duration: int
    embeddable_by: str
    genre: str | None = None
    id: int
    kind: Literal["playlist"]
    label_name: str | None
    last_modified: datetime
    license: str
    likes_count: int
    managed_by_feeds: bool
    permalink: str
    permalink_url: str
    public: bool
    purchase_title: str | None
    purchase_url: str | None
    release_date: str | None
    reposts_count: int
    secret_token: str | None
    sharing: str
    tag_list: str
    title: str
    uri: str
    user_id: int
    set_type: str
    is_album: bool
    published_at: str | None
    display_date: datetime
    user: User
    tracks: list[Track | TrackSlim]
    track_count: int


class Reposted(BaseModel):
    target_urn: str
    user_urn: str
    caption: str | None


class BaseCollection(BaseModel):
    created_at: datetime
    user: User
    uuid: str
    caption: str | None


class PlaylistCollection(BaseCollection):
    """Posted playlists"""

    type: Literal["playlist"]
    playlist: Playlist


class PlaylistRepostCollection(BaseCollection):
    """Posted playlists"""

    type: Literal["playlist-repost"]
    playlist: Playlist
    reposted: Reposted


class TrackRepostCollection(BaseCollection):
    """Reposted tracks"""

    type: Literal["track-repost"]
    track: Track
    reposted: Reposted


class TrackCollection(BaseCollection):
    """Posted tracks"""

    type: Literal["track"]
    track: Track


Collection = Annotated[
    PlaylistRepostCollection | PlaylistCollection | TrackRepostCollection | TrackCollection,
    Field(discriminator="type"),
]

CollectionType = Literal["playlist", "playlist-repost", "track", "track-repost"]


class GetStream(BaseModel):
    collection: list[Collection]
    next_href: str | None
    query_urn: str | None


SearchCollection = Annotated[Playlist | Track | User, Field(discriminator="kind")]


class SearchResponse(BaseModel):
    collection: list[SearchCollection]
    next_href: str | None = None
    query_urn: str | None = None
    total_results: int

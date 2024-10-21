from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from soundcloud_tools.models.user import User

type TrackID = int


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
    def hq_artwork_url(self) -> str | None:
        return self.artwork_url and self.artwork_url.replace("-large.", "-t500x500.")

    @property
    def artist(self) -> str:
        return (self.publisher_metadata and self.publisher_metadata.artist) or self.user.username

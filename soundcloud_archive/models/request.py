from pydantic import BaseModel

from soundcloud_archive.models.playlist import PlaylistCreate


class PlaylistCreateRequest(BaseModel):
    playlist: PlaylistCreate

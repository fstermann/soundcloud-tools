from pydantic import BaseModel

from soundcloud_tools.models.playlist import PlaylistCreate


class PlaylistCreateRequest(BaseModel):
    playlist: PlaylistCreate

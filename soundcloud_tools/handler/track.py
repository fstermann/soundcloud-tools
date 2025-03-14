from datetime import date
from pathlib import Path
from typing import Self

import pydub
import requests
from mutagen.aiff import AIFF
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3, TCON, TDRC, TDRL, TIT2, TPE1
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from soundcloud_tools.models import Track
from soundcloud_tools.utils import convert_to_int, load_tracks

FILETYPE_MAP = {
    ".mp3": MP3,
    ".aif": AIFF,
    ".aiff": AIFF,
    ".wav": WAVE,
}


class TrackInfo(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    title: str
    artist: str | list[str]
    genre: str
    year: int
    release_date: str
    artwork: bytes | None = None
    artwork_url: str | None = None

    artist_options: set[str] = Field(default_factory=set)

    @model_validator(mode="after")
    def check_artwork_url(self):
        if self.artwork_url and not self.artwork:
            self.artwork = requests.get(self.artwork_url).content
        return self

    @property
    def filename(self) -> str:
        return f"{self.artist_str} - {self.title}"

    @property
    def complete(self) -> bool:
        return all([self.title, self.artist, self.genre, self.year, self.release_date, self.artwork])

    @property
    def artist_str(self) -> str:
        artists = [self.artist] if isinstance(self.artist, str) else self.artist
        return ", ".join(artists)

    @classmethod
    def from_sc_track(cls, track: Track) -> Self:
        artist_options = {
            track.publisher_metadata and track.publisher_metadata.artist,
            track.user.username,
            track.title.split(" - ")[0],
        }
        most_likely_artist = sorted(
            artist_options,
            key=lambda a: int(a in track.title) + int(a in track.title.split(" - ")[0]),  # type: ignore[operator]
            reverse=True,
        )
        return cls(
            title=track.title,
            artist=(most_likely_artist and most_likely_artist[0]) or "",
            genre=track.genre or "",
            year=track.display_date.year,
            release_date=track.display_date.strftime("%Y-%m-%d"),
            artwork_url=track.hq_artwork_url or track.user.hq_avatar_url,
            artist_options={a for a in artist_options if a},
        )

    @property
    def release_date_obj(self) -> date:
        return date.fromisoformat(self.release_date)


class TrackHandler(BaseModel):
    root_folder: Path
    file: Path
    bitrate: int = 320

    @field_validator("root_folder", "file", mode="before")
    @classmethod
    def check_paths(cls, v) -> Path:
        if isinstance(v, str):
            v = Path(v)
        return v

    @classmethod
    def load_all(cls, root_folder: Path) -> list[Self]:
        return [cls(root_folder=root_folder, file=f) for f in load_tracks(root_folder)]

    @classmethod
    def load_track_infos(cls, folder: Path):
        return [t.track_info for t in cls.load_all(folder)]

    @property
    def cleaned_folder(self):
        return self.root_folder / "cleaned"

    @property
    def prepare_folder(self):
        return self.root_folder / "prepare"

    @property
    def archive_folder(self):
        return self.root_folder / "archive"

    def delete(self):
        self.file.unlink()
        return

    @property
    def mp3_file(self):
        return self.cleaned_folder / (self.file.stem + ".mp3")

    @property
    def track(self):
        class_ = FILETYPE_MAP.get(Path(self.file).suffix, EasyID3)
        obj = class_(self.file)
        if not hasattr(obj, "tags") or obj.tags is None:
            obj.add_tags()
        return obj

    @property
    def track_info(self):
        track = self.track
        return TrackInfo(
            title=str(track.tags.get("TIT2", "")),
            artist=str(track.tags.get("TPE1", "")).split("\u0000"),
            genre=str(track.tags.get("TCON", "")),
            year=convert_to_int(str(track.tags.get("TDRC", 0)), default=0),
            release_date=str(track.tags.get("TDRL", "")),
            artwork=self.get_single_cover(raise_error=False),
        )

    @property
    def covers(self):
        return self.track.tags.getall("APIC")

    def get_single_cover(self, raise_error: bool = True):
        if len(self.covers) != 1:
            if raise_error:
                raise ValueError("Track has more than one cover")
            return self.covers[0].data if self.covers else None
        return self.covers[0].data

    def convert_to_mp3(self):
        if not self.cleaned_folder.exists():
            self.cleaned_folder.mkdir(parents=True)
        sound = pydub.AudioSegment.from_file(self.file)
        sound.export(self.mp3_file, format="mp3", bitrate=f"{self.bitrate}k")
        return self.mp3_file

    def move_to_cleaned(self):
        if not self.cleaned_folder.exists():
            self.cleaned_folder.mkdir(parents=True)
        safe_name = self.file.name.replace("/", "-")
        self.file.rename(self.cleaned_folder / safe_name)

    def update_release_date(self, release_date: str):
        track = self.track
        track.tags.delall("TDRL")
        track.tags.add(TDRL(encoding=3, text=release_date))
        track.save()

    def set_genre(self, genre: str):
        track = self.track
        track.tags.delall("TCON")
        track.tags.add(TCON(encoding=3, text=genre))
        track.save()

    def _add_info(self, track, info: TrackInfo, artwork: bytes | None = None):
        track.add(TIT2(encoding=3, text=info.title))
        track.add(TPE1(encoding=3, text=info.artist))
        track.add(TCON(encoding=3, text=info.genre))
        track.add(TDRC(encoding=3, text=str(info.year)))
        track.add(TDRL(encoding=3, text=info.release_date))
        if artwork:
            track.delall("APIC")
            track.add(
                APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=artwork,
                )
            )

    def add_info(self, info: TrackInfo, artwork: bytes | None = None):
        track = self.track
        self._add_info(track.tags, info=info, artwork=artwork)
        track.save()

    def add_mp3_info(self):
        track = ID3(str(self.mp3_file))
        self._add_info(track, info=self.track_info, artwork=self.get_single_cover())
        track.save()

    def archive(self):
        if not self.archive_folder.exists():
            self.archive_folder.mkdir(parents=True)
        self.file.rename(self.archive_folder / self.file.name)

    def rename(self, new_name: str):
        safe_name = new_name.replace("/", "-")
        return self.file.rename(Path(self.file.parent, safe_name + self.file.suffix))

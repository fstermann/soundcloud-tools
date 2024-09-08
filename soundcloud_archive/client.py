import logging
from datetime import datetime
from typing import Any, Callable

import devtools
import httpx
from pydantic import BaseModel, Field, TypeAdapter
from starlette.routing import compile_path

from soundcloud_archive.models import Collection, CollectionType, CreatePlaylist, GetStream, PlaylistCreate, TrackID
from soundcloud_archive.settings import get_settings
from soundcloud_archive.utils import Weekday, get_default_kwargs, get_scheduled_time, get_week_of_month

logger = logging.getLogger(__name__)


class SplitParams(BaseModel):
    client: Any
    path_params: dict = Field(default_factory=dict)
    query_params: dict = Field(default_factory=dict)
    data: dict | None = None
    content: str | None = None
    kwargs: dict = Field(default_factory=dict)

    @classmethod
    async def from_route(cls, client: Any, endpoint: Callable, path: str, **kwargs):
        full_kwargs = get_default_kwargs(endpoint) | kwargs
        params = cls(client=client)

        additional_params = await endpoint(client, **kwargs) or {}
        _, _, path_param_names = compile_path(path)
        expected_path_params = set(path_param_names)

        params.kwargs = full_kwargs.pop("kwargs", {})
        # Use kwargs defined in endpoint
        params.kwargs.update(additional_params.pop("kwargs", {}))
        params.data = full_kwargs.pop("data", None) or additional_params.get("data")
        if params.data and (data_type := endpoint.__annotations__.get("data")):
            # Store the data as a JSON String, in order to get the validation
            # benefits from the TypeAdapter
            params.content = TypeAdapter(data_type).dump_json(params.data)
        params.path_params = {k: v for k, v in full_kwargs.items() if k in expected_path_params}
        params.query_params = {k: v for k, v in full_kwargs.items() if k not in expected_path_params}
        params.query_params.update(additional_params.get("query", {}))
        # If query params are passed as a dict, move them to the query_params
        params.query_params.update(params.query_params.pop("params", {}))
        return params


def route(method: str, path: str, response_model: BaseModel | None = None):
    def wrapper(endpoint_func):
        async def caller(self, **kwargs):
            split_params = await SplitParams.from_route(client=self, endpoint=endpoint_func, path=path, **kwargs)
            url = self.make_url(path, **split_params.path_params)
            params = self.json_dump(split_params.query_params)
            response = await self.make_request(
                method,
                url,
                content=split_params.content,
                params=params,
                **split_params.kwargs,
            )
            response_data = response.json()
            if not response_model:
                return response_data
            return TypeAdapter(response_model).validate_python(response_data)

        return caller

    return wrapper


class Client:
    def __init__(self, base_url: str = get_settings().base_url):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"OAuth {get_settings().oauth_token}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "x-datadome-clientid": get_settings().datadome_clientid,
            },
            params={
                "client_id": get_settings().client_id,
                "app_version": "1725276048",
                "app_locale": "en",
            },
        )

    def json_dump(self, data: Any):
        return data if not isinstance(data, BaseModel) else data.model_dump(mode="json")

    async def make_request(self, method: str, url: str, **kwargs):
        response = await self.client.request(method, url, **kwargs)
        logger.info(f"Response {response.status_code} for {method} {response.url}")
        return response

    def make_url(self, path: str, **path_params: str) -> str:
        return f"{self.client.base_url}/{path.format(**path_params)}"

    @route("POST", "playlists")
    async def post_playlist(self, data: CreatePlaylist): ...

    @route("GET", "playlists/{playlist_id}")
    async def get_playlist(self, playlist_id: int, show_tracks: bool = True): ...

    @route("GET", "users/{user_id}/likes/tracks")
    async def get_user_likes(self, user_id: int): ...

    @route("GET", "users/{user_id}/followings/ids")
    async def get_user_followings_ids(self, user_id: int, limit: int = 5000, linked_partitioning: bool = True): ...

    @route("GET", "users/{user_id}/followers/ids")
    async def get_user_followers_ids(self, user_id: int, limit: int = 5000, linked_partitioning: bool = True): ...

    @route("GET", "tracks/{track_id}")
    async def get_track(self, track_id: int): ...

    @route("GET", "stream", response_model=GetStream)
    async def get_stream(
        self,
        user_urn: str,
        promoted_playlist: bool = True,
        limit: int = 100,
        offset: int = 0,
        linked_partitioning: bool = True,
    ): ...


async def get_collections(
    client: Client, user_id: int, start: datetime, end: datetime, exclude_own: bool = True
) -> list[TrackID]:
    limit, offset = 100, 0
    user_urn = f"soundcloud:users:{user_id}"
    all_reposts = []
    while True:
        response: GetStream = await client.get_stream(user_urn=user_urn, offset=offset)
        reposts = [
            c
            for c in response.collection
            if start < c.created_at < end and (c.user.id != user_id if exclude_own else True)
        ]
        logger.info(f"Found {len(reposts)} valid reposts")
        all_reposts += reposts
        if not reposts:
            break
        offset += limit
    return all_reposts


def get_track_ids_from_collections(collections: list[Collection], types: list[CollectionType]) -> set[int]:
    track_ids = set()
    for c in collections:
        if c.type not in types:
            continue
        if c.type.startswith("playlist"):
            track_ids |= {t.id for t in c.playlist.tracks}
        if c.type.startswith("track"):
            track_ids.add(c.track.id)
    return track_ids


async def get_tracks_ids_in_timespan(
    client: Client, user_id: int, start: datetime, end: datetime, types: list[CollectionType]
):
    collections = await get_collections(client, user_id=user_id, start=start, end=end)
    track_ids = get_track_ids_from_collections(collections, types=types)
    logger.info(f"Found {len(track_ids)} tracks")
    return track_ids


async def create_weekly_favorite_playlist(client: Client, user_id: int, types: list[CollectionType], week: int = 0):
    logger.info(f"Creating weekly favorite playlist for {week = } and {types = }")
    start = get_scheduled_time(Weekday.SUNDAY, weeks=week - 1)
    end = get_scheduled_time(Weekday.SUNDAY, weeks=week)
    month, week_of_month = start.strftime("%b"), get_week_of_month(start)

    track_ids = await get_tracks_ids_in_timespan(client, user_id=user_id, start=start, end=end, types=types)

    # Create playlist from track_ids
    playlist = CreatePlaylist(
        playlist=PlaylistCreate(
            title=f"Weekly Favorites {month.upper()}/{week_of_month}",
            description=(
                f"Autogenerated set of liked and reposted tracks from my favorite artists.\n"
                f"Week {week_of_month} of {month} "
                f"({start.date()} - {end.date()}, CW {start.isocalendar().week})"
            ),
            tracks=list(track_ids),
            sharing="private",
            tag_list=f"soundcloud-archive,weekly-favorites,{month.upper()}/{week_of_month},CW{start.isocalendar().week}",
        )
    )
    request = devtools.pformat(playlist.model_dump(exclude={"playlist": {"tracks"}}))
    logger.info(f"Creating playlist {request} with {len(track_ids)} tracks")
    await client.post_playlist(data=playlist)
    return track_ids

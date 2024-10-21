import json
import logging
import urllib.parse as urlparse
from typing import Any, Callable

import requests
from pydantic import BaseModel, Field, TypeAdapter
from starlette.routing import compile_path

from soundcloud_tools import models as scm
from soundcloud_tools.models.request import PlaylistCreateRequest
from soundcloud_tools.settings import get_settings
from soundcloud_tools.utils import generate_random_user_agent, get_default_kwargs

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
            logger.info(f"Making request to {url}")
            response = await self.make_request(
                method,
                url,
                data=split_params.content,
                params=params,
                **split_params.kwargs,
            )
            try:
                response_data = response.json()
            except json.decoder.JSONDecodeError:
                logger.error(f"Failed to decode response (status: {response.status_code})\n{response.text}")
                return
            if not response_model:
                return response_data
            return TypeAdapter(response_model).validate_python(response_data)

        return caller

    return wrapper


class Client:
    def __init__(self, base_url: str = get_settings().base_url):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"OAuth {get_settings().oauth_token}",
            "User-Agent": generate_random_user_agent(),
            "x-datadome-clientid": get_settings().datadome_clientid,
        }
        self.params = {
            "client_id": get_settings().client_id,
            "app_version": "1725276048",
            "app_locale": "en",
        }
        self.proxies = {"https://": "https://" + get_settings().proxy} if get_settings().proxy else {}

    def json_dump(self, data: Any):
        return data if not isinstance(data, BaseModel) else data.model_dump(mode="json")

    async def make_request(self, method: str, url: str, **kwargs):
        kwargs.setdefault("params", self.params)
        kwargs.setdefault("headers", self.headers)
        if get_settings().proxy:
            kwargs.setdefault("proxies", self.proxies)
        kwargs.setdefault("verify", False)
        response = requests.request(method, url, **kwargs)
        logger.info(f"Response {response.status_code} for {method} {response.url}")
        return response

    def _make_request(self, *arg, **kwargs):
        return self.make_request(*arg, **kwargs)

    def make_url(self, path: str, **path_params: str) -> str:
        return f"{self.base_url}/{path.format(**path_params)}"

    @staticmethod
    def get_next_offset(href: str) -> str | None:
        parsed = urlparse.urlparse(href)
        offset = urlparse.parse_qs(parsed.query).get("offset") or None
        return offset and offset[0]

    @route("POST", "playlists")
    async def post_playlist(self, data: PlaylistCreateRequest): ...

    @route("GET", "playlists/{playlist_id}")
    async def get_playlist(self, playlist_id: int, show_tracks: bool = True): ...

    @route("GET", "users/{user_id}/likes", response_model=scm.Likes)
    async def get_user_likes(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        linked_partitioning: bool = True,
    ): ...

    @route("GET", "stream/users/{user_id}/reposts", response_model=scm.Reposts)
    async def get_user_reposts(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
        linked_partitioning: bool = True,
    ): ...

    @route("GET", "users/{user_id}/followings/ids")
    async def get_user_followings_ids(self, user_id: int, limit: int = 5000, linked_partitioning: bool = True): ...

    @route("GET", "users/{user_id}/followers/ids")
    async def get_user_followers_ids(self, user_id: int, limit: int = 5000, linked_partitioning: bool = True): ...

    @route("GET", "tracks/{track_id}")
    async def get_track(self, track_id: int): ...

    @route("GET", "stream", response_model=scm.Stream)
    async def get_stream(
        self,
        user_urn: str,
        promoted_playlist: bool = True,
        limit: int = 100,
        offset: int = 0,
        linked_partitioning: bool = True,
    ): ...

    @route("GET", "search", response_model=scm.Search)
    async def search(self, q: str, limit: int = 20, offset: int = 0): ...

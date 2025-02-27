from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Setttings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", env_file=".env")

    base_url: str = "https://api-v2.soundcloud.com"
    oauth_token: str
    client_id: str
    user_id: int
    datadome_clientid: str = ""
    sc_a_id: str = ""

    proxy: str | None = None


@lru_cache(maxsize=1)
def get_settings():
    return Setttings()

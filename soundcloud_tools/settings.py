from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class HypedditSettings(BaseModel):
    """Configuration for the Hypeddit automation."""

    name: str
    email: str
    comment: str = "<3"


class Setttings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", env_file=".env")

    base_url: str = "https://api-v2.soundcloud.com"
    oauth_token: str
    client_id: str
    datadome_clientid: str
    user_id: int
    sc_a_id: str

    proxy: str | None = None
    hypeddit: HypedditSettings


@lru_cache(maxsize=1)
def get_settings():
    return Setttings()

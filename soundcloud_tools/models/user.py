from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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

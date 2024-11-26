from pydantic import BaseModel


class Followings(BaseModel):
    collection: list[int]
    next_href: str | None
    query_urn: str | None

import logging
from datetime import datetime
from typing import Literal

import devtools

from soundcloud_tools.client import Client
from soundcloud_tools.models.comment import Comment
from soundcloud_tools.models.playlist import PlaylistCreate
from soundcloud_tools.models.request import PlaylistCreateRequest
from soundcloud_tools.models.stream import Stream, StreamItem, StreamItemType
from soundcloud_tools.utils import Weekday, get_scheduled_time, get_week_of_month

logger = logging.getLogger(__name__)


Items = StreamItemType | Literal["comment"]


async def get_collections(
    client: Client, user_id: int, start: datetime, end: datetime, exclude_own: bool = True
) -> list[StreamItem | Comment]:
    reposts = await get_reposts(client, user_id, start, end, exclude_own)
    comments = await get_comments(client, user_id, start, end, exclude_own)
    return reposts + comments


async def get_all_user_likes(client: Client, user_id: int):
    limit, offset = 100, 0
    all_tracks = []
    while True:
        response: Stream = await client.get_user_likes(user_id=user_id, limit=limit, offset=offset)
        tracks = [like.track for like in response.collection if hasattr(like, "track")]
        logger.info(f"Found {len(tracks)} valid reposts")
        all_tracks += tracks
        if not tracks:
            break
        offset += limit
    return all_tracks


async def get_reposts(
    client: Client, user_id: int, start: datetime, end: datetime, exclude_own: bool = True
) -> list[StreamItem]:
    limit, offset = 100, 0
    user_urn = f"soundcloud:users:{user_id}"
    all_reposts = []
    while True:
        response: Stream = await client.get_stream(user_urn=user_urn, limit=limit, offset=offset)
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


async def get_comments(
    client: Client, user_id: int, start: datetime, end: datetime, exclude_own: bool = True
) -> list[Comment]:
    all_comments = []
    followings = await client.get_user_followings_ids(user_id=user_id)
    for user_id in followings.collection:
        limit, offset = 100, 0
        while True:
            response: Stream = await client.get_user_comments(user_id=user_id, limit=limit, offset=offset)
            comments = [
                c
                for c in response.collection
                if start < c.created_at < end and (c.user.id != user_id if exclude_own else True)
            ]
            logger.info(f"Found {len(comments)} valid comments")
            all_comments += comments
            if not comments:
                break
            offset += limit
    return all_comments


def get_track_ids_from_collections(collections: list[StreamItem | Comment], types: list[Items]) -> set[int]:
    track_ids = set()
    for c in collections:
        if c.type not in types:
            continue
        if c.type.startswith("playlist"):
            track_ids |= {t.id for t in c.playlist.tracks}
        if c.type.startswith("track"):
            track_ids.add(c.track.id)
        if c.type.startswith("comment"):
            track_ids.add(c.track_id)
    return track_ids


async def get_tracks_ids_in_timespan(client: Client, user_id: int, start: datetime, end: datetime, types: list[Items]):
    collections = []
    if "track" in types or "track-repost" in types:
        collections += await get_reposts(client, user_id, start=start, end=end, exclude_own=True)
    if "comment" in types:
        collections += await get_comments(client, user_id, start=start, end=end, exclude_own=True)

    track_ids = get_track_ids_from_collections(collections, types=types)
    logger.info(f"Found {len(track_ids)} tracks")
    return track_ids


async def create_weekly_favorite_playlist(
    client: Client, user_id: int, types: list[Items], week: int = 0, exclude_liked: bool = False
):
    logger.info(f"Creating weekly favorite playlist for {week = } and {types = }")
    start = get_scheduled_time(Weekday.SUNDAY, weeks=week - 1)
    end = get_scheduled_time(Weekday.SUNDAY, weeks=week)
    month, week_of_month = start.strftime("%b"), get_week_of_month(start)

    track_ids = await get_tracks_ids_in_timespan(client, user_id=user_id, start=start, end=end, types=types)
    if exclude_liked:
        logger.info("Removing likes tracks")
        liked_tracks = get_all_user_likes(client, user_id=user_id)
        liked_track_ids = {track.id for track in liked_tracks}
        track_ids = list(set(track_ids) - liked_track_ids)
        logger.info(f"Found {len(track_ids)} tracks after removing liked tracks")

    # Create playlist from track_ids
    playlist = PlaylistCreateRequest(
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

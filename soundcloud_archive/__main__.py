import asyncio
import logging

from soundcloud_archive.client import Client, create_weekly_favorite_playlist
from soundcloud_archive.settings import get_settings


def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.run(
        create_weekly_favorite_playlist(
            client=Client(),
            user_id=get_settings().user_id,
            types=["track-repost", "track"],
        )
    )


if __name__ == "__main__":
    main()

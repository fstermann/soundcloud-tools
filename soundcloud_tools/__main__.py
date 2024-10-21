import argparse
import asyncio
import logging

from soundcloud_tools.client import Client
from soundcloud_tools.settings import get_settings
from soundcloud_tools.weekly import create_weekly_favorite_playlist


def main(week: int = 0):
    logging.basicConfig(level=logging.INFO)
    asyncio.run(
        create_weekly_favorite_playlist(
            client=Client(),
            user_id=get_settings().user_id,
            types=["track-repost", "track"],
            week=week,
        )
    )


def main_script():
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", type=int, default=0)
    args = parser.parse_args()
    main(week=args.week)


if __name__ == "__main__":
    main_script()

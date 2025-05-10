import argparse
import asyncio
import logging
from typing import Literal

from soundcloud_tools.client import Client
from soundcloud_tools.settings import get_settings
from soundcloud_tools.weekly import create_weekly_favorite_playlist


def main(
    week: int = 0,
    exclude_liked: bool = False,
    half: Literal["first", "second"] | None = None,
    release_type: Literal["new", "old"] | None = None,
    dry_run: bool = False,
):
    logging.basicConfig(level=logging.INFO)
    asyncio.run(
        create_weekly_favorite_playlist(
            client=Client(),
            user_id=get_settings().user_id,
            types=["track-repost", "track"],
            week=week,
            exclude_liked=exclude_liked,
            half=half,
            release_type=release_type,
            dry_run=dry_run,
        )
    )


def main_script():
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", type=int, default=0)
    parser.add_argument("--first", action="store_true")
    parser.add_argument("--second", action="store_true")
    parser.add_argument("--exclude-liked", action="store_true")
    parser.add_argument("--release-type", type=str, default=None, choices=["new", "old"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.first and args.second:
        raise ValueError("Cannot specify both first and second half")
    main(
        week=args.week,
        exclude_liked=args.exclude_liked,
        half="first" if args.first else "second" if args.second else None,
        release_type=args.release_type,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main_script()

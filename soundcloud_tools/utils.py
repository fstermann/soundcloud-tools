import inspect
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from math import ceil
from typing import Any

from fake_useragent import UserAgent


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


def get_scheduled_time(day: Weekday = Weekday.SUNDAY, weeks: int = 0):
    now = datetime.now(tz=timezone.utc)
    days_since = now.weekday() % day
    last_day = now + timedelta(days=-days_since, weeks=weeks)
    return last_day.replace(hour=8, minute=0, second=0, microsecond=0)


def get_week_of_month(date: datetime) -> Weekday:
    """Returns the week of the month for the specified date."""
    first_day = date.replace(day=1)
    dom = date.day
    adjusted_dom = dom + first_day.weekday()

    return Weekday(int(ceil(adjusted_dom / 7.0)))


def get_default_kwargs(func):
    signature = inspect.signature(func)
    return {k: v.default for k, v in signature.parameters.items() if v.default is not inspect.Parameter.empty}


def generate_random_user_agent() -> str:
    return UserAgent().random


def convert_to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

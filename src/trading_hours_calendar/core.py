from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Callable, Dict, List, Mapping, Optional, Tuple


SESSION_TYPES = {}


class SessionType(Enum):
    REGULAR = "regular"
    HALF_DAY = "half_day"


class SessionStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True)
class Session:
    date: date
    open_time: time
    close_time: time
    session_type: SessionType


from datetime import datetime


def _parse_time(value):
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError(f"time must be 'HH:MM', got {value!r}")
        hh, mm = parts
        return time(int(hh), int(mm))
    raise TypeError(f"time must be datetime.time or str, got {type(value).__name__}")


@dataclass(frozen=True)
class WeekSpec:
    start_time: time
    close_time: time
    half_close_time: time
    weekdays: Tuple[int, ...]
    first_weekend_day: int

    def is_weekend(self, weekday: int) -> bool:
        days = {self.first_weekend_day, (self.first_weekend_day + 1) % 7}
        return weekday in days

    def __post_init__(self) -> None:
        if not 0 <= self.first_weekend_day <= 6:
            raise ValueError("first_weekend_day must be 0..6")
        if self.first_weekend_day in self.weekdays:
            raise ValueError(
                "first_weekend_day must not appear in weekdays; "
                "the weekend is {first_weekend_day} and {(first_weekend_day + 1) % 7}"
            )


@dataclass
class ExchangeSchedule:
    week: WeekSpec
    holidays: Dict[date, None] = field(default_factory=dict)
    half_days: Dict[date, None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.holidays = dict(self.holidays)
        self.half_days = dict(self.half_days)

    def session_for_date(self, d: date) -> Optional[Session]:
        if d in self.holidays:
            return None
        if self.week.is_weekend(d.weekday()):
            return None
        if d in self.half_days:
            return Session(
                date=d,
                open_time=self.week.start_time,
                close_time=self.week.half_close_time,
                session_type=SessionType.HALF_DAY,
            )
        return Session(
            date=d,
            open_time=self.week.start_time,
            close_time=self.week.close_time,
            session_type=SessionType.REGULAR,
        )

    def is_open_at(self, dt: datetime) -> bool:
        sess = self.session_for_date(dt.date())
        if sess is None:
            return False
        if dt.time() < sess.open_time or dt.time() >= sess.close_time:
            return False
        return True

    def status_at(self, dt: datetime) -> SessionStatus:
        return SessionStatus.OPEN if self.is_open_at(dt) else SessionStatus.CLOSED

    def sessions_in_range(self, start: date, end: date) -> List[Session]:
        if end < start:
            return []
        out: List[Session] = []
        d = start
        one = timedelta(days=1)
        while d <= end:
            s = self.session_for_date(d)
            if s is not None:
                out.append(s)
            d += one
        return out


def _us_week() -> WeekSpec:
    return WeekSpec(
        start_time=_parse_time("09:30"),
        close_time=_parse_time("16:00"),
        half_close_time=_parse_time("13:00"),
        weekdays=(0, 1, 2, 3, 4),
        first_weekend_day=5,
    )


def _gcc_week() -> WeekSpec:
    return WeekSpec(
        start_time=_parse_time("10:00"),
        close_time=_parse_time("15:00"),
        half_close_time=_parse_time("12:00"),
        weekdays=(0, 1, 2, 3, 6),
        first_weekend_day=4,
    )


def _ldn_week() -> WeekSpec:
    return WeekSpec(
        start_time=_parse_time("08:00"),
        close_time=_parse_time("16:30"),
        half_close_time=_parse_time("12:30"),
        weekdays=(0, 1, 2, 3, 4),
        first_weekend_day=5,
    )


def _tky_week() -> WeekSpec:
    return WeekSpec(
        start_time=_parse_time("09:00"),
        close_time=_parse_time("15:00"),
        half_close_time=_parse_time("13:00"),
        weekdays=(0, 1, 2, 3, 4),
        first_weekend_day=5,
    )


def _sgp_week() -> WeekSpec:
    return WeekSpec(
        start_time=_parse_time("09:00"),
        close_time=_parse_time("17:00"),
        half_close_time=_parse_time("13:00"),
        weekdays=(0, 1, 2, 3, 4),
        first_weekend_day=5,
    )


class Exchange:
    NYSE = ExchangeSchedule(week=_us_week())
    LSE = ExchangeSchedule(week=_ldn_week())
    TPE = ExchangeSchedule(week=_tky_week())
    SGX = ExchangeSchedule(week=_sgp_week())
    TADAWUL = ExchangeSchedule(week=_gcc_week())


__all__ = [
    "Exchange",
    "ExchangeSchedule",
    "Session",
    "SessionType",
    "SessionStatus",
    "WeekSpec",
]

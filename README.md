# trading-hours-calendar

Determines market open/close times for global stock exchanges, handling weekend shifts (e.g. GCC Friday/Saturday weekends) and half-day sessions. Standard library only; no timezone database, no network.

## Usage

```python
from datetime import date, datetime
from trading_hours_calendar import Exchange, ExchangeSchedule, WeekSpec, SessionStatus
from datetime import time

# Use a predefined exchange
nyse = Exchange.NYSE
print(nyse.is_open_at(datetime(2024, 1, 3, 12, 0)))  # True

# Build a custom exchange with a Friday/Saturday weekend
tadawul = ExchangeSchedule(
    week=WeekSpec(
        start_time=time(10, 0),
        close_time=time(15, 0),
        half_close_time=time(12, 0),
        weekdays=(0, 1, 2, 3, 6),  # Sun-Thu
        first_weekend_day=4,        # Friday; Saturday is the second weekend day
    ),
)
print(tadawul.session_for_date(date(2024, 1, 7)))  # Sunday session
```

Exported names: `Exchange`, `ExchangeSchedule`, `WeekSpec`, `Session`, `SessionType`, `SessionStatus`.

## Why this exists

Trading-hours logic looks trivial until you meet markets whose weekend is not Saturday/Sunday, or whose close time on the day before a holiday is half the usual. Pulling in a full IANA timezone database to answer "is NYSE open right now?" is overkill and unkind to containers. This library trades correctness-at-any-instant for a small, explicit model: you declare the weekly pattern, the holiday dates, and the half-day dates, and the library tells you the rest.

## The awkward edge

All datetimes passed to `is_open_at` are interpreted as exchange-local wall-clock time. The library does not convert timezones. If your "now" is in UTC and the exchange is in New York, convert before asking. A clock function is not wired in by design: pass the datetime you want evaluated, which makes the behaviour trivially deterministic in tests.

The interval is half-open: `open <= t < close`. At exactly `close_time` the market is closed.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.


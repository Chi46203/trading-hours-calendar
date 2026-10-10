import unittest
from datetime import date, datetime, time, timedelta

from trading_hours_calendar import (
    Exchange,
    ExchangeSchedule,
    Session,
    SessionStatus,
    SessionType,
    WeekSpec,
)


class TestWeekSpec(unittest.TestCase):
    def test_us_weekend_is_sat_sun(self):
        w = WeekSpec(
            start_time=time(9, 30),
            close_time=time(16, 0),
            half_close_time=time(13, 0),
            weekdays=(0, 1, 2, 3, 4),
            first_weekend_day=5,
        )
        # 2024-01-06 is Saturday, 2024-01-07 is Sunday.
        self.assertTrue(w.is_weekend(date(2024, 1, 6).weekday()))
        self.assertTrue(w.is_weekend(date(2024, 1, 7).weekday()))
        self.assertFalse(w.is_weekend(date(2024, 1, 5).weekday()))  # Friday

    def test_gcc_weekend_is_fri_sat(self):
        w = WeekSpec(
            start_time=time(10, 0),
            close_time=time(15, 0),
            half_close_time=time(12, 0),
            weekdays=(0, 1, 2, 3, 6),
            first_weekend_day=4,
        )
        self.assertTrue(w.is_weekend(4))  # Friday
        self.assertTrue(w.is_weekend(5))  # Saturday
        self.assertFalse(w.is_weekend(6))  # Sunday (trading day)

    def test_weekend_wraps_sunday_to_monday(self):
        # Tadawul weekend = Sat(5)/Sun(6). Sunday wraps to 6, Saturday is 5.
        w = WeekSpec(
            start_time=time(10, 0),
            close_time=time(15, 0),
            half_close_time=time(12, 0),
            weekdays=(0, 1, 2, 3, 4),
            first_weekend_day=6,
        )
        self.assertTrue(w.is_weekend(6))  # Sunday
        self.assertTrue(w.is_weekend(0))  # Monday (wrap)
        self.assertFalse(w.is_weekend(5))  # Saturday (trading day)


class TestExchangeScheduleSessions(unittest.TestCase):
    def setUp(self):
        self.nyse = ExchangeSchedule(
            week=WeekSpec(
                start_time=time(9, 30),
                close_time=time(16, 0),
                half_close_time=time(13, 0),
                weekdays=(0, 1, 2, 3, 4),
                first_weekend_day=5,
            ),
            holidays={date(2024, 7, 4): None},
            half_days={date(2024, 11, 29): None},
        )

    def test_regular_session_on_weekday(self):
        d = date(2024, 1, 3)  # Wednesday
        s = self.nyse.session_for_date(d)
        self.assertIsNotNone(s)
        self.assertEqual(s.date, d)
        self.assertEqual(s.open_time, time(9, 30))
        self.assertEqual(s.close_time, time(16, 0))
        self.assertEqual(s.session_type, SessionType.REGULAR)

    def test_weekend_yields_no_session(self):
        self.assertIsNone(self.nyse.session_for_date(date(2024, 1, 6)))  # Sat
        self.assertIsNone(self.nyse.session_for_date(date(2024, 1, 7)))  # Sun

    def test_holiday_yields_no_session(self):
        self.assertIsNone(self.nyse.session_for_date(date(2024, 7, 4)))

    def test_half_day_uses_shorter_close_and_half_day_type(self):
        s = self.nyse.session_for_date(date(2024, 11, 29))  # Friday half-day
        self.assertIsNotNone(s)
        self.assertEqual(s.close_time, time(13, 0))
        self.assertEqual(s.session_type, SessionType.HALF_DAY)


class TestIsOpenAt(unittest.TestCase):
    def setUp(self):
        self.nyse = ExchangeSchedule(
            week=WeekSpec(
                start_time=time(9, 30),
                close_time=time(16, 0),
                half_close_time=time(13, 0),
                weekdays=(0, 1, 2, 3, 4),
                first_weekend_day=5,
            ),
            half_days={date(2024, 11, 29): None},
        )

    def test_open_mid_morning(self):
        self.assertTrue(self.nyse.is_open_at(datetime(2024, 1, 3, 12, 0)))

    def test_closed_before_open(self):
        self.assertFalse(self.nyse.is_open_at(datetime(2024, 1, 3, 9, 0)))

    def test_closed_at_exact_close(self):
        # Open interval end: close_time is closed.
        self.assertFalse(self.nyse.is_open_at(datetime(2024, 1, 3, 16, 0)))

    def test_open_at_exact_open(self):
        self.assertTrue(self.nyse.is_open_at(datetime(2024, 1, 3, 9, 30)))

    def test_closed_on_weekend(self):
        self.assertFalse(self.nyse.is_open_at(datetime(2024, 1, 6, 12, 0)))

    def test_half_day_closes_earlier(self):
        self.assertTrue(self.nyse.is_open_at(datetime(2024, 11, 29, 12, 0)))
        self.assertFalse(self.nyse.is_open_at(datetime(2024, 11, 29, 13, 0)))

    def test_status_at_returns_enum(self):
        self.assertEqual(
            self.nyse.status_at(datetime(2024, 1, 3, 12, 0)),
            SessionStatus.OPEN,
        )
        self.assertEqual(
            self.nyse.status_at(datetime(2024, 1, 3, 22, 0)),
            SessionStatus.CLOSED,
        )


class TestSessionsInRange(unittest.TestCase):
    def setUp(self):
        self.nyse = ExchangeSchedule(
            week=WeekSpec(
                start_time=time(9, 30),
                close_time=time(16, 0),
                half_close_time=time(13, 0),
                weekdays=(0, 1, 2, 3, 4),
                first_weekend_day=5,
            ),
            holidays={date(2024, 1, 1): None},
        )

    def test_range_skips_holidays_and_weekends(self):
        # 2024-01-01 Mon holiday, 02-05 Tue-Fri trading, 06-07 weekend.
        sessions = self.nyse.sessions_in_range(date(2024, 1, 1), date(2024, 1, 8))
        self.assertEqual(len(sessions), 5)
        self.assertEqual([s.date for s in sessions],
                         [date(2024, 1, 2), date(2024, 1, 3),
                          date(2024, 1, 4), date(2024, 1, 5),
                          date(2024, 1, 8)])

    def test_inverted_range_returns_empty(self):
        self.assertEqual(self.nyse.sessions_in_range(date(2024, 1, 8), date(2024, 1, 1)), [])

    def test_single_date_range(self):
        sessions = self.nyse.sessions_in_range(date(2024, 1, 3), date(2024, 1, 3))
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].date, date(2024, 1, 3))


class TestPredefinedExchanges(unittest.TestCase):
    def test_nyse_predefined_regular(self):
        s = Exchange.NYSE.session_for_date(date(2024, 1, 3))
        self.assertIsNotNone(s)
        self.assertEqual(s.open_time, time(9, 30))
        self.assertEqual(s.close_time, time(16, 0))

    def test_tadawul_predefined_uses_gcc_weekend(self):
        # 2024-01-05 is Friday; Tadawul is closed.
        self.assertIsNone(Exchange.TADAWUL.session_for_date(date(2024, 1, 5)))
        # 2024-01-07 is Sunday; Tadawul trades.
        s = Exchange.TADAWUL.session_for_date(date(2024, 1, 7))
        self.assertIsNotNone(s)
        self.assertEqual(s.open_time, time(10, 0))
        self.assertEqual(s.close_time, time(15, 0))

    def test_lse_predefined_times(self):
        s = Exchange.LSE.session_for_date(date(2024, 1, 3))
        self.assertIsNotNone(s)
        self.assertEqual(s.open_time, time(8, 0))
        self.assertEqual(s.close_time, time(16, 30))


class TestSessionDataclass(unittest.TestCase):
    def test_session_is_frozen(self):
        s = Session(
            date=date(2024, 1, 3),
            open_time=time(9, 30),
            close_time=time(16, 0),
            session_type=SessionType.REGULAR,
        )
        with self.assertRaises(Exception):
            s.open_time = time(10, 0)  # type: ignore[misc]


class TestCustomWeekWithMidweekWeekend(unittest.TestCase):
    """Some Gulf markets historically used Thu/Fri weekends."""

    def test_thursday_friday_weekend(self):
        w = WeekSpec(
            start_time=time(10, 0),
            close_time=time(15, 0),
            half_close_time=time(12, 0),
            weekdays=(0, 1, 2, 6),  # Sun-Wed, Sun=6? Actually Mon=0..Wed=2 plus Sun=6.
            first_weekend_day=3,  # Thursday
        )
        self.assertTrue(w.is_weekend(3))  # Thursday
        self.assertTrue(w.is_weekend(4))  # Friday
        self.assertFalse(w.is_weekend(5))  # Saturday (trading)
        self.assertFalse(w.is_weekend(6))  # Sunday (trading)


class TestWeekSpecValidation(unittest.TestCase):
    def test_first_weekend_day_out_of_range(self):
        with self.assertRaises(ValueError):
            WeekSpec(
                start_time=time(9, 30),
                close_time=time(16, 0),
                half_close_time=time(13, 0),
                weekdays=(0, 1, 2, 3, 4),
                first_weekend_day=7,
            )

    def test_first_weekend_day_in_weekdays(self):
        with self.assertRaises(ValueError):
            WeekSpec(
                start_time=time(9, 30),
                close_time=time(16, 0),
                half_close_time=time(13, 0),
                weekdays=(0, 1, 2, 3, 4, 5),
                first_weekend_day=5,
            )


if __name__ == "__main__":
    unittest.main()

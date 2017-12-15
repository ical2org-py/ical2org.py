from datetime import datetime, timedelta

import pytest

from pytz import timezone, utc

from ical2orgpy import add_delta_dst, advance_just_before

# Timezone in Prague
PRAGUE = timezone("Europe/Prague")
# UTC
UTC = timezone("UTC")


# TODO: Add some cases spanning DST borders
@pytest.mark.parametrize(
    "dt, delta, expected",
    [(datetime(2017, 12, 15, 12, 0, 0, 0, PRAGUE), timedelta(hours=1),
      datetime(2017, 12, 15, 13, 0, 0, 0, PRAGUE)),
     (datetime(2017, 12, 15, 12, 0, 0, 0, PRAGUE), timedelta(days=1),
      datetime(2017, 12, 16, 12, 0, 0, 0, PRAGUE))],
    ids=lambda itm: str(itm))
def test_add_delta_dst(dt, delta, expected):
    res = add_delta_dst(dt, delta)
    assert isinstance(res, datetime)
    assert hasattr(res, "tzinfo")
    delta = (res - expected).total_seconds()
    # tolerate 5 minutes difference (yes, it happens)
    assert abs(delta) < 5 * 60


@pytest.mark.parametrize("start_dt, timeframe_start, delta_days, expected",
                         [(datetime(2003, 2, 1, 1, 0, 0, 0, PRAGUE),
                           datetime(2017, 9, 16, 18, 57, 53, 0, PRAGUE), 7,
                           (datetime(2017, 9, 9, 1, 0, 0, 0, PRAGUE), 762))],
                         ids=lambda itm: str(itm))
def test_advance_just_before(start_dt, timeframe_start, delta_days, expected):
    res = advance_just_before(start_dt, timeframe_start, delta_days)
    res_dt, res_int = res
    exp_dt, exp_int = expected
    assert res_int == exp_int
    assert res_dt.year == exp_dt.year
    assert res_dt.month == exp_dt.month
    assert res_dt.day == exp_dt.day
    assert res_dt.hour == exp_dt.hour
    assert res_dt.minute == exp_dt.minute

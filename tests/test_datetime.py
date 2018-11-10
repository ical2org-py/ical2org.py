"""Test functions related to simple time conversions.
"""
from datetime import date, datetime

import pytest
from pytz import timezone, utc

from ical2orgpy import orgDatetime, orgDate, get_datetime

# Timezone in Prague
PRAGUE = timezone("Europe/Prague")
# UTC
UTC = timezone("UTC")


@pytest.mark.parametrize(
    "dt, tz, expected", [
        (datetime(2017, 12, 15, 17, 35, 0, 0, UTC), PRAGUE,
         "<2017-12-15 Fri 18:35>"),
        (datetime(2017, 12, 15, 18, 35, 0, 0, UTC), PRAGUE,
         "<2017-12-15 Fri 19:35>"),
    ],
    ids=lambda itm: str(itm))
def test_org_datetime(dt, tz, expected):
    res = orgDatetime(dt, tz)
    assert res == expected


@pytest.mark.parametrize(
    "dt, tz, expected", [
        (datetime(2017, 12, 15, 17, 35, 0, 0, UTC), PRAGUE,
         "<2017-12-15 Fri>"),
        (datetime(2017, 12, 15, 18, 35, 0, 0, UTC), PRAGUE,
         "<2017-12-15 Fri>"),
    ],
    ids=lambda itm: str(itm))
def test_org_date(dt, tz, expected):
    res = orgDate(dt, tz)
    assert res == expected


@pytest.mark.parametrize(
    "dt, tz, expected", [
        (datetime(2017, 12, 15, 17, 35, 0, 0, UTC), PRAGUE,
         datetime(2017, 12, 15, 17, 35, 0, 0, UTC)),
        (datetime(2017, 12, 15, 18, 35, 0, 0, PRAGUE), PRAGUE,
         datetime(2017, 12, 15, 18, 35, 0, 0, PRAGUE)),
        (datetime(2017, 12, 15, 17, 35, 0, 0), PRAGUE,
         datetime(2017, 12, 15, 17, 35, 0, 0, PRAGUE)),
        (date(2017, 12, 15), PRAGUE,
         datetime(2017, 12, 15, 1, 0, 0, 0, PRAGUE)),
    ],
    ids=lambda itm: str(itm))
def test_get_datetime_datetime(dt, tz, expected):
    """test conversion of a datetime or naive date into time-aware datetime.

    Unfortunately, timezones are a bit messy and one can encounter
    e.g. 2 minutes difference between two datetimes, which look exactly
    the same, but you may learn about PMT timezone returned for Europe/Paris.
    """
    res = get_datetime(dt, tz)
    assert isinstance(res, datetime)
    assert hasattr(res, "tzinfo")
    delta = (res - expected).total_seconds()
    # tolerate 5 minutes difference (yes, it happens)
    assert abs(delta) < 5 * 60

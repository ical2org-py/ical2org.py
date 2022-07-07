"""Test functions related to simple time conversions.
"""
from datetime import datetime

import pytest
from pytz import timezone

from ical2orgpy import org_datetime, org_date

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
    res = org_datetime(dt, tz)
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
    res = org_date(dt, tz)
    assert res == expected

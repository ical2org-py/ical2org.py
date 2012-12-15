#!/usr/bin/python2.7

import sys
from math import floor
from datetime import date, datetime, timedelta, tzinfo
from icalendar import Calendar, Event

REC_DELTAS = { 'YEARLY' : 365,
               'WEEKLY' :  7,
               'DAILY'  :  1 }

# These tzinfo classes are taken from python documentation

ZERO = timedelta(0)
HOUR = timedelta(hours=1)

# A UTC class.

class UTC_tz(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

# A class capturing the platform's idea of local time.

import time as _time

STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class Local_tz(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

def canonical_date(d):
    '''Given a date or a datetime, return the equivalent datetime in UTC timezone'''
    # d can be date or datetime
    try:
        return d.astimezone(UTC_tz())
    except AttributeError:
        # d is date. Convert to datetime.
        new_dt = datetime(year = d.year, month = d.month, day = d.day, tzinfo = Local_tz())
        return  new_dt.astimezone(UTC_tz())

def orgDate(dt):
    '''given a datetime in UTC, return YYYY-MM-DD DayofWeek HH:MM using local timezone'''
    return dt.astimezone(Local_tz()).strftime("<%Y-%m-%d %a %H:%M>")

def recurring_events(rec_start, rec_end, delta_str, interval_start, interval_end):

    result = []
    rec_duration = rec_end - rec_start
    delta_days = REC_DELTAS[delta_str]
    delta = timedelta(days = delta_days)
    if rec_start < interval_start:
        delta_ord = (interval_start.toordinal() - rec_start.toordinal()) / delta_days
        date_aux = rec_start + timedelta(days = delta_days * int(delta_ord))
        while date_aux < interval_start:
            date_aux += delta
    else :
        date_aux = rec_start

    delta = timedelta(days = delta_days)
    end = interval_end
    if rec_end > interval_start and rec_end < interval_end: end = rec_end
    while date_aux < end:
        result.append( (date_aux, date_aux + rec_duration, 1) )
        date_aux += delta
    return result

def inBetween(comp, start, end):
    '''Check whether component lies between start and end'''
    if comp.name != 'VEVENT': return []
    comp_start=canonical_date(comp['DTSTART'].dt)
    comp_end=canonical_date(comp['DTEND'].dt)
    if 'RRULE' in comp:
        # recurring event. Return true unless the event it's over
        if 'UNTIL' in comp['RRULE']:
            finish_date = canonical_date(comp['RRULE']['UNTIL'][0])
        else :
            finish_date = end
        if finish_date < start: return []
        return recurring_events(comp_start, comp_end, comp['RRULE']['FREQ'][0], start, finish_date)
    if comp_start > end: return []
    if comp_end < start: return []
    return [ (comp_start, comp_end, 0) ]

if len(sys.argv) < 2:
    sys.exit('Usage: {0} file.ics'.format(sys.argv[0]))
    sys.exit(1)

progname, ifname = sys.argv

cal = Calendar.from_ical(open(ifname,'rb').read())
#cal = Calendar.from_ical(open('kk.ics','rb').read())
# cal = Calendar.from_ical(open('basic.ics','rb').read())

now=canonical_date(datetime.now(Local_tz()))
start = now - timedelta( days = +30)
end = now + timedelta( days = +30)
for comp in cal.walk():
    for comp_start, comp_end, rec_event in inBetween(comp, start, end):
        print("* {}".format(comp['SUMMARY'].to_ical())),
        if rec_event:
            print(" :RECURRING:")
        else:
            print("")
        print("{}--{}".format(orgDate(comp_start), orgDate(comp_end)))

#!/usr/bin/python2.7

import sys
from datetime import date, datetime, timedelta, tzinfo
from icalendar import Calendar, Event

REC_DELTAS = { 'YEARLY' : 365,
               'WEEKLY' :  7,
               'DAILY'  :  1 }

# This tzinfo classes are taken from python documentation
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
            return timedelta(0)

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

local_tz = Local_tz()

def canonical_date(d):
    '''Given a date or a datetime, return a canonical date
       . first, convert the datetime to local time
       . then, remove timezone
    '''
    # d can be date or datetime
    try:
        new_dt = d.astimezone(local_tz)
        return new_dt.replace(tzinfo = None)
    except AttributeError:
        # d is date. Being a naive date, let's suppose it is in local timezone.
        return  datetime(year = d.year, month = d.month, day = d.day)

def orgDate(dt):
    '''given a datetime in UTC, return YYYY-MM-DD DayofWeek HH:MM'''
    return dt.strftime("<%Y-%m-%d %a %H:%M>")

def recurring_events(event_start, event_end, delta_str, interval_start, interval_end):

    result = []
    event_duration = event_end - event_start
    delta_days = REC_DELTAS[delta_str]
    delta = timedelta(days = delta_days)
    if event_start < interval_start:
        delta_ord = (interval_start.toordinal() - event_start.toordinal()) / delta_days
        date_aux = event_start + timedelta(days = delta_days * int(delta_ord))
        while date_aux < interval_start:
            date_aux += delta
    else :
        date_aux = event_start

    delta = timedelta(days = delta_days)
    end = interval_end
    if event_end > interval_start and event_end < interval_end:
        end = event_end
    while date_aux < end:
        result.append( (date_aux, date_aux + event_duration, 1) )
        date_aux += delta
    return result

def inBetween(comp, start, end):
    '''Check whether VEVENT component lies between start and end'''
    if comp.name != 'VEVENT': return []
    event_start=canonical_date(comp['DTSTART'].dt)
    event_end=canonical_date(comp['DTEND'].dt)
    if 'RRULE' in comp:
        if 'UNTIL' in comp['RRULE']:
            event_until = canonical_date(comp['RRULE']['UNTIL'][0])
        else :
            event_until = end
        if event_until < start: return []
        event_until = max (event_until, end)
        return recurring_events(event_start, event_end, comp['RRULE']['FREQ'][0], start, event_until)
    if event_start > end: return []
    if event_end < start: return []
    return [ (event_start, event_end, 0) ]

if len(sys.argv) < 2:
    sys.exit('Usage: {0} file.ics'.format(sys.argv[0]))
    sys.exit(1)

progname, ifname = sys.argv

cal = Calendar.from_ical(open(ifname,'rb').read())
#cal = Calendar.from_ical(open('kk.ics','rb').read())
# cal = Calendar.from_ical(open('basic.ics','rb').read())

now = canonical_date(datetime.now(local_tz))
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

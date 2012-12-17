#!/usr/bin/python2.7

import sys
from datetime import date, datetime, timedelta, tzinfo
from icalendar import Calendar
from pytz import timezone, utc

# Change here your local timezone
LOCAL_TZ = timezone("Europe/Paris")
# Window lenght in days (left & right from current time). Has to be possitive.
WINDOW = 90
# leave empty if you don't want to attach any tag to recurring events
RECUR_TAG = ":RECURRING:"

# Do not change anything below

REC_DELTAS = { 'YEARLY' : 365,
               'WEEKLY' :  7,
               'DAILY'  :  1 }

def get_datetime(dt):
    '''Given a datetime, return it. If argument is date, convert it to a local datetime'''
    if isinstance(dt, datetime):
        return dt
    else:
        # d is date. Being a naive date, let's suppose it is in local
        # timezone.  Unfortunately using the tzinfo argument of the standard
        # datetime constructors ''does not work'' with pytz for many
        # timezones, so create first a utc datetime, and convert to local timezone
        aux_dt = datetime(year = dt.year, month = dt.month, day = dt.day, tzinfo = utc)
        return aux_dt.astimezone(LOCAL_TZ)

def orgDate(dt):
    '''Given a datetime return YYYY-MM-DD DayofWeek HH:MM in local timezone'''
    return dt.astimezone(LOCAL_TZ).strftime("<%Y-%m-%d %a %H:%M>")

def add_delta_dst(dt, delta):
    '''Add a timedelta to a datetime, adjusting DST when appropriate'''
    # convert datetime to naive, add delta and convert again to specified timezone
    naive_dt = dt.replace(tzinfo = None)
    return dt.tzinfo.localize(naive_dt + delta)

def recurring_events(event_start, event_end, delta_str, interval_start, interval_end):

    result = []
    event_duration = event_end - event_start
    delta_days = REC_DELTAS[delta_str]
    delta = timedelta(days = delta_days)
    if event_start < interval_start:
        delta_ord = (interval_start.toordinal() - event_start.toordinal()) / delta_days
        date_aux = add_delta_dst(event_start, timedelta(days = delta_days * int(delta_ord)))
        while date_aux < interval_start:
            date_aux = add_delta_dst(date_aux, delta)
    else :
        date_aux = event_start

    delta = timedelta(days = delta_days)
    end = interval_end
    if event_end > interval_start and event_end < interval_end:
        end = event_end
    while date_aux < end:
        result.append( (date_aux, date_aux + event_duration, 1) )
        date_aux = add_delta_dst(date_aux, delta)
    return result

def eventsBetween(comp, start, end):
    '''Check whether VEVENT component lies between start and end, and, if
    so, return it. If recurring event, return all apropriate events, i.e.,
    those which fall within the interval.'''
    if comp.name != 'VEVENT': return []
    event_start=get_datetime(comp['DTSTART'].dt)
    event_end=get_datetime(comp['DTEND'].dt)
    if 'RRULE' in comp:
        if 'UNTIL' in comp['RRULE']:
            event_until = get_datetime(comp['RRULE']['UNTIL'][0])
        else :
            event_until = end
        if event_until < start: return []
        event_until = max(event_until, end)
        return recurring_events(event_start, event_end, comp['RRULE']['FREQ'][0], start, event_until)
    # Single event
    if event_start > end: return []
    if event_end < start: return []
    return [ (event_start, event_end, 0) ]

# main function here

if len(sys.argv) < 2:
    sys.exit('Usage: {0} file.ics'.format(sys.argv[0]))
    sys.exit(1)

progname, ifname = sys.argv
cal = Calendar.from_ical(open(ifname,'rb').read())

now = datetime.now(LOCAL_TZ)
start = now - timedelta( days = WINDOW)
end = now + timedelta( days = WINDOW)
for comp in cal.walk():
    for comp_start, comp_end, rec_event in eventsBetween(comp, start, end):
        print("* {}".format(comp['SUMMARY'].to_ical())),
        if rec_event and len(RECUR_TAG):
            print(" {}".format(RECUR_TAG))
        else:
            print("")
        print("  {}--{}".format(orgDate(comp_start), orgDate(comp_end)))

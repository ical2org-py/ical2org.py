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

REC_DELTAS = { 'WEEKLY' :  7,
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
    '''Given a datetime in his own timezone, return YYYY-MM-DD DayofWeek HH:MM in local timezone'''
    return dt.astimezone(LOCAL_TZ).strftime("<%Y-%m-%d %a %H:%M>")

def add_delta_dst(dt, delta):
    '''Add a timedelta to a datetime, adjusting DST when appropriate'''
    # convert datetime to naive, add delta and convert again to his own timezone
    naive_dt = dt.replace(tzinfo = None)
    return dt.tzinfo.localize(naive_dt + delta)

def recurring_event_years(event_start, event_end, start_utc, end_utc):
    result = []
    event_duration = event_end - event_start
    for frame_year in range(start_utc.year, end_utc.year + 1):
        event_aux = event_start.replace(year=frame_year)
        if event_aux > start_utc and event_aux < end_utc:
            result.append( (event_aux, event_aux.tzinfo.normalize(event_aux + event_duration), 1) )
    return result

def recurring_event_days(event_start, event_end, delta_str, start_utc, end_utc):
    result = []
    if delta_str not in REC_DELTAS:
        return []
    event_duration = event_end - event_start
    delta_days = REC_DELTAS[delta_str]
    delta = timedelta(days = delta_days)
    if event_start < start_utc:
        delta_ord = (start_utc.toordinal() - event_start.toordinal()) / delta_days
        event_aux = add_delta_dst(event_start, timedelta(days = delta_days * int(delta_ord)))
        while event_aux < start_utc:
            event_aux = add_delta_dst(event_aux, delta)
    else :
        event_aux = event_start

    while event_aux < end_utc:
        result.append( (event_aux, event_aux.tzinfo.normalize(event_aux + event_duration), 1) )
        event_aux = add_delta_dst(event_aux, delta)
    return result

def recurring_events(event_start, event_end, delta_str, start_utc, end_utc):
    # event_start, event_end specified using its own timezone
    # start_utc, end_utc specified using UTC
    if delta_str == 'YEARLY':
        return recurring_event_years(event_start, event_end, start_utc, end_utc)
    return recurring_event_days(event_start, event_end, delta_str, start_utc, end_utc)

def eventsBetween(comp, start_utc, end_utc):
    '''Check whether VEVENT component lies between start and end, and, if
    so, return it. If recurring event, return all apropriate events, i.e.,
    those which fall within the interval.'''
    if comp.name != 'VEVENT': return []
    event_start=get_datetime(comp['DTSTART'].dt)
    event_end=get_datetime(comp['DTEND'].dt)
    if 'RRULE' in comp:
        if 'UNTIL' in comp['RRULE']:
            event_until = get_datetime(comp['RRULE']['UNTIL'][0]).astimezone(utc)
        else :
            event_until = end_utc
        if event_until < start_utc: return []
        event_until = max(event_until, end_utc)
        return recurring_events(event_start, event_end, comp['RRULE']['FREQ'][0], start_utc, event_until)
    # Single event
    if event_start > end_utc: return []
    if event_end < start_utc: return []
    return [ (event_start, event_end, 0) ]

# main function here

if len(sys.argv) < 2:
    sys.exit('Usage: {0} file.ics'.format(sys.argv[0]))
    sys.exit(1)

progname, ifname = sys.argv
cal = Calendar.from_ical(open(ifname,'rb').read())

now = datetime.now(utc)
start = now - timedelta( days = WINDOW)
end = now + timedelta( days = WINDOW)
for comp in cal.walk():
    try:
        for comp_start, comp_end, rec_event in eventsBetween(comp, start, end):
            if 'SUMMARY' in comp:
                print("* {}".format(comp['SUMMARY'].to_ical())),
            else:
                print("* (no title)"),
            if rec_event and len(RECUR_TAG):
                print(" {}".format(RECUR_TAG))
            else:
                print("")
            print("  {}--{}".format(orgDate(comp_start), orgDate(comp_end)))
    except:
        pass

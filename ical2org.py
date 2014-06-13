#!/usr/bin/python2.7

from __future__ import print_function
import sys
from math import floor
from datetime import date, datetime, timedelta, tzinfo
from icalendar import Calendar
from pytz import timezone, utc

# Change here your local timezone
LOCAL_TZ = timezone("Europe/Paris")
# Window length in days (left & right from current time). Has to be positive.
WINDOW = 90
# leave empty if you don't want to attach any tag to recurring events
RECUR_TAG = ":RECURRING:"

# Do not change anything below

def orgDate(dt):
    '''Given a datetime in his own timezone, return YYYY-MM-DD DayofWeek HH:MM in local timezone'''
    return dt.astimezone(LOCAL_TZ).strftime("<%Y-%m-%d %a %H:%M>")

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

def add_delta_dst(dt, delta):
    '''Add a timedelta to a datetime, adjusting DST when appropriate'''
    # convert datetime to naive, add delta and convert again to his own timezone
    naive_dt = dt.replace(tzinfo = None)
    return dt.tzinfo.localize(naive_dt + delta)

def advance_just_before(start_dt, timeframe_start, delta_days):
    '''Advance an start_dt datetime to the first date just before
    timeframe_start. Use delta_days for advancing the event. Precond:
    start_dt < timeframe_start'''
    delta = timedelta(days = delta_days)
    delta_ord = floor( (timeframe_start.toordinal() - start_dt.toordinal() - 1) / delta_days )
    return (add_delta_dst(start_dt, timedelta(days = delta_days * int(delta_ord))), int(delta_ord))


def generate_event_iterator(comp, timeframe_start, timeframe_end):
    ''' Given an VEVENT object return an iterator with the proper delta (days, weeks, etc)'''
    # Note: timeframe_start and timeframe_end are in UTC
    if comp.name != 'VEVENT': return []
    if 'RRULE' in comp:
        return {
            'WEEKLY' : EventRecurDaysIter(7, comp, timeframe_start, timeframe_end),
            'DAILY' : EventRecurDaysIter(1, comp, timeframe_start, timeframe_end),
            'MONTHLY' : [],
            'YEARLY' : EventRecurYearlyIter(comp, timeframe_start, timeframe_end)
            }[ comp['RRULE']['FREQ'][0] ]
    else:
        return EventSingleIter(comp, timeframe_start, timeframe_end)

class EventSingleIter:
    '''Iterator for non-recurring single events.'''
    def __init__(self, comp, timeframe_start, timeframe_end):
        self.ev_start = get_datetime(comp['DTSTART'].dt)
        self.ev_end = get_datetime(comp['DTEND'].dt)
        self.duration = self.ev_end - self.ev_start
        self.result = ()
        if (self.ev_start < timeframe_end and self.ev_end > timeframe_start):
            self.result = ( self.ev_start, self.ev_end, 0)

    def __iter__(self):
        return self

    # Iterate just once
    def next(self):
        if self.result:
            aux = self.result
            self.result = ()
        else:
            raise StopIteration
        return aux

class EventRecurDaysIter:
    '''Iterator for daily-based recurring events (daily, weekly).'''
    def __init__(self, days, comp, timeframe_start, timeframe_end):
        self.ev_start = get_datetime(comp['DTSTART'].dt)
        self.ev_end = get_datetime(comp['DTEND'].dt)
        self.duration = self.ev_end - self.ev_start
        self.is_count = False
        if 'COUNT' in comp['RRULE']:
            self.is_count = True
            self.count = comp['RRULE']['COUNT'][0]
        delta_days = days
        if 'INTERVAL' in comp['RRULE']:
            delta_days *= comp['RRULE']['INTERVAL'][0]
        self.delta = timedelta(delta_days)
        if 'UNTIL' in comp['RRULE']:
            if self.is_count:
                raise "UNTIL and COUNT MUST NOT occur in the same 'recur'"
            self.until_utc = get_datetime(comp['RRULE']['UNTIL'][0]).astimezone(utc)
        else :
            self.until_utc = timeframe_end
        if self.until_utc < timeframe_start:
            self.current = self.until_utc + self.delta # Default value for no iteration
            return
        self.until_utc = min(self.until_utc, timeframe_end)
        if self.ev_start < timeframe_start:
            # advance to timeframe start
            (self.current, counts) = advance_just_before(self.ev_start, timeframe_start, delta_days)
            if self.is_count:
                self.count -= counts
                if self.count < 1: return
            while self.current < timeframe_start:
                self.current = add_delta_dst(self.current, self.delta)
        else:
            self.current = self.ev_start

    def __iter__(self):
        return self

    def next_until(self):
        if self.current > self.until_utc:
            raise StopIteration
        event_aux = self.current
        self.current = add_delta_dst(self.current, self.delta)
        return (event_aux, event_aux.tzinfo.normalize(event_aux + self.duration), 1)

    def next_count(self):
        if self.count < 1:
            raise StopIteration
        self.count -= 1
        event_aux = self.current
        self.current = add_delta_dst(self.current, self.delta)
        return (event_aux, event_aux.tzinfo.normalize(event_aux + self.duration), 1)

    def next(self):
        if self.is_count: return self.next_count()
        return self.next_until()

class EventRecurMonthlyIter:
    pass

class EventRecurYearlyIter:
    def __init__(self, comp, timeframe_start, timeframe_end):
        self.ev_start = get_datetime(comp['DTSTART'].dt)
        self.ev_end = get_datetime(comp['DTEND'].dt)
        self.start = timeframe_start
        self.end = timeframe_end
        self.is_until = False
        if 'UNTIL' in comp['RRULE']:
            self.is_until = True
            self.end = min(self.end, get_datetime(comp['RRULE']['UNTIL'][0]).astimezone(utc))
        if self.end < self.start:
            # Default values for no iteration
            self.i = 0
            self.n = 0
            return
        if 'BYMONTH' in comp['RRULE']:
            self.bymonth = comp['RRULE']['BYMONTH'][0]
        else:
            self.bymonth = self.ev_start.month
        if 'BYMONTHDAY' in comp['RRULE']:
            self.bymonthday = comp['RRULE']['BYMONTHDAY'][0]
        else:
            self.bymonthday = self.ev_start.day
        self.duration = self.ev_end - self.ev_start
        self.years = range(self.start.year, self.end.year + 1)
        if 'COUNT' in comp['RRULE']:
            if self.is_until:
                raise "UNTIL and COUNT MUST NOT occur in the same 'recur'"
            self.years = range(self.ev_start.year, self.end.year + 1)
            del self.years[comp['RRULE']['COUNT'][0]:]
        self.i = 0
        self.n = len(self.years)

    def __iter__(self):
        return self

    def next(self):
        if self.i >= self.n: raise StopIteration
        event_aux = self.ev_start.replace(year = self.years[self.i])
        event_aux = event_aux.replace(month = self.bymonth)
        event_aux = event_aux.replace(day = self.bymonthday)
        self.i = self.i + 1;
        if event_aux > self.end: raise StopIteration
        if event_aux < self.start: return self.next()
        return (event_aux, event_aux.tzinfo.normalize(event_aux + self.duration), 1)

if len(sys.argv) < 2:
    fh = sys.stdin
else:
    fh = open(sys.argv[1],'rb')

if len(sys.argv) > 2:
    fh_w = open(sys.argv[2],'wb')
else:
    fh_w = sys.stdout

try:
    cal = Calendar.from_ical(fh.read())
except:
    print("ERROR parsing ical file", file=sys.stderr)
    exit(1)
    pass

now = datetime.now(utc)
start = now - timedelta( days = WINDOW)
end = now + timedelta( days = WINDOW)
for comp in cal.walk():
    try:
        event_iter = generate_event_iterator(comp, start, end)
        for comp_start, comp_end, rec_event in event_iter:
            SUMMARY = ""
            if "SUMMARY" in comp:
                SUMMARY = comp['SUMMARY'].to_ical()
                SUMMARY = SUMMARY.replace('\\,', ',')
            if not len(SUMMARY):
                SUMMARY = "(No title)"
            fh_w.write("* {}".format(SUMMARY))
            if rec_event and len(RECUR_TAG):
                fh_w.write(" {}\n".format(RECUR_TAG))
            fh_w.write("\n")
            fh_w.write("  {}--{}\n".format(orgDate(comp_start), orgDate(comp_end)))
            if 'DESCRIPTION' in comp:
                DESCRIPTION = '\n'.join(comp['DESCRIPTION'].to_ical().split('\\n'))
                DESCRIPTION = DESCRIPTION.replace('\\,', ',')
                fh_w.write("{}\n".format(DESCRIPTION))

            fh_w.write("\n")
    except:
        pass
exit(0);

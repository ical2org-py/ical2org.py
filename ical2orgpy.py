from __future__ import print_function
import sys
from math import floor
from datetime import date, datetime, timedelta, tzinfo
from icalendar import Calendar
from pytz import timezone, utc


def print_error(msg):
    print(msg, file=sys.stderr)


def orgDatetime(dt, local_tz):
    '''Timezone aware datetime to YYYY-MM-DD DayofWeek HH:MM str in localtime.
    '''
    return dt.astimezone(local_tz).strftime("<%Y-%m-%d %a %H:%M>")


def orgDate(dt, local_tz):
    '''Timezone aware date to YYYY-MM-DD DayofWeek in localtime.
    '''
    return dt.astimezone(local_tz).strftime("<%Y-%m-%d %a>")


def get_datetime(dt, local_tz):
    '''Convert date or datetime to local datetime.
    '''
    if isinstance(dt, datetime):
        return dt
    else:
        # d is date. Being a naive date, let's suppose it is in local
        # timezone.  Unfortunately using the tzinfo argument of the standard
        # datetime constructors ''does not work'' with pytz for many
        # timezones, so create first a utc datetime, and convert to local
        # timezone
        aux_dt = datetime(year=dt.year, month=dt.month, day=dt.day, tzinfo=utc)
        return aux_dt.astimezone(local_tz)


def add_delta_dst(dt, delta):
    '''Add a timedelta to a datetime, adjusting DST when appropriate'''
    # convert datetime to naive, add delta and convert again to his own
    # timezone
    naive_dt = dt.replace(tzinfo=None)
    return dt.tzinfo.localize(naive_dt + delta)


def advance_just_before(start_dt, timeframe_start, delta_days):
    '''Advance an start_dt datetime to the first date just before
    timeframe_start. Use delta_days for advancing the event. Precond:
    start_dt < timeframe_start'''
    delta = timedelta(days=delta_days)
    delta_ord = floor(
        (timeframe_start.toordinal() - start_dt.toordinal() - 1) / delta_days)
    return (add_delta_dst(
        start_dt, timedelta(days=delta_days * int(delta_ord))), int(delta_ord))


def generate_event_iterator(comp, timeframe_start, timeframe_end, local_tz):
    '''Get iterator with the proper delta (days, weeks, etc)'''
    # Note: timeframe_start and timeframe_end are in UTC
    if comp.name != 'VEVENT':
        return []
    if 'RRULE' in comp:
        return {
            'WEEKLY':
            EventRecurDaysIter(7, comp, timeframe_start, timeframe_end,
                               local_tz),
            'DAILY':
            EventRecurDaysIter(1, comp, timeframe_start, timeframe_end,
                               local_tz),
            'MONTHLY': [],
            'YEARLY':
            EventRecurYearlyIter(comp, timeframe_start, timeframe_end,
                                 local_tz)
        }[comp['RRULE']['FREQ'][0]]
    else:
        return EventSingleIter(comp, timeframe_start, timeframe_end, local_tz)


class EventSingleIter(object):
    '''Iterator for non-recurring single events.'''

    def __init__(self, comp, timeframe_start, timeframe_end, local_tz):
        self.ev_start = get_datetime(comp['DTSTART'].dt, local_tz)

        # Events with the same begin/end time same do not include
        # "DTEND".
        if "DTEND" not in comp:
            self.ev_end = self.ev_start
        else:
            self.ev_end = get_datetime(comp['DTEND'].dt, local_tz)

        self.duration = self.ev_end - self.ev_start
        self.result = ()
        if (self.ev_start < timeframe_end and self.ev_end > timeframe_start):
            self.result = (self.ev_start, self.ev_end, 0)

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


class EventRecurDaysIter(object):
    '''Iterator for daily-based recurring events (daily, weekly).'''

    def __init__(self, days, comp, timeframe_start, timeframe_end, local_tz):
        self.ev_start = get_datetime(comp['DTSTART'].dt, local_tz)
        self.ev_end = get_datetime(comp['DTEND'].dt, local_tz)
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
                msg = "UNTIL and COUNT MUST NOT occur in the same 'recur'"
                raise ValueError(msg)
            self.until_utc = get_datetime(comp['RRULE']['UNTIL'][0],
                                          local_tz).astimezone(utc)
        else:
            self.until_utc = timeframe_end
        if self.until_utc < timeframe_start:
            # Default value for no iteration
            self.current = self.until_utc + self.delta
            return
        self.until_utc = min(self.until_utc, timeframe_end)
        if self.ev_start < timeframe_start:
            # advance to timeframe start
            (self.current, counts) = advance_just_before(
                self.ev_start, timeframe_start, delta_days)
            if self.is_count:
                self.count -= counts
                if self.count < 1:
                    return
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
        return (event_aux,
                event_aux.tzinfo.normalize(event_aux + self.duration), 1)

    def next_count(self):
        if self.count < 1:
            raise StopIteration
        self.count -= 1
        event_aux = self.current
        self.current = add_delta_dst(self.current, self.delta)
        return (event_aux,
                event_aux.tzinfo.normalize(event_aux + self.duration), 1)

    def next(self):
        if self.is_count:
            return self.next_count()
        return self.next_until()


class EventRecurMonthlyIter(object):
    pass


class EventRecurYearlyIter(object):
    def __init__(self, comp, timeframe_start, timeframe_end, local_tz):
        self.ev_start = get_datetime(comp['DTSTART'].dt, local_tz)
        self.ev_end = get_datetime(comp['DTEND'].dt, local_tz)
        self.start = timeframe_start
        self.end = timeframe_end
        self.is_until = False
        if 'UNTIL' in comp['RRULE']:
            self.is_until = True
            self.end = min(self.end,
                           get_datetime(comp['RRULE']['UNTIL'][0],
                                        local_tz).astimezone(utc))
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
                msg = "UNTIL and COUNT MUST NOT occur in the same 'recur'"
                raise ValueError(msg)
            self.years = range(self.ev_start.year, self.end.year + 1)
            del self.years[comp['RRULE']['COUNT'][0]:]
        self.i = 0
        self.n = len(self.years)

    def __iter__(self):
        return self

    def next(self):
        if self.i >= self.n:
            raise StopIteration
        event_aux = self.ev_start.replace(year=self.years[self.i])
        event_aux = event_aux.replace(month=self.bymonth)
        event_aux = event_aux.replace(day=self.bymonthday)
        self.i = self.i + 1
        if event_aux > self.end:
            raise StopIteration
        if event_aux < self.start:
            return self.next()
        return (event_aux,
                event_aux.tzinfo.normalize(event_aux + self.duration), 1)


class IcalParsingError(Exception):
    pass


def main():
    """Convert input stream in ICAL format into org-mode format on output.

    Input is read from stdin or first positional argument.

    Output is either stdout or the first non-input file name argument.

    ::

        $ cat in.ical | ical2orgpy > out.org
        $ cat in.ical | ical2orgpy out.org
        $ ical2orgpy in.ical > out.org
        $ ical2orgpy in.ical out.org
    """
    if (len(sys.argv) == 1) or ("-h" in sys.argv) or ("--help" in sys.argv):
        print(main.__doc__)
        sys.exit(0)
    # TODO: get following default values from command line options
    default_window = 90
    default_tz = "Europe/Paris"

    to_close = []

    if len(sys.argv) < 2:
        fh = sys.stdin
    else:
        try:
            fh = open(sys.argv[1], 'rb')
            to_close.append(fh)
        except IOError as e:
            print_error(e)
            sys.exit(1)

    if len(sys.argv) > 2:
        try:
            fh_w = open(sys.argv[2], 'wb')
            to_close.append(fh_w)
        except IOError as e:
            print_error(e)
            sys.exit(1)
    else:
        fh_w = sys.stdout
    convertor = Convertor(default_window, default_tz)
    try:
        convertor(fh, fh_w)
        sys.exit(0)
    except IcalParsingError as e:
        print_error(e)
        sys.exit(1)
    finally:
        for f in to_close:
            f.close()
    sys.exit(1)


class Convertor(object):
    RECUR_TAG = ":RECURRING:"

    # Do not change anything below

    def __init__(self, window=90, default_tz="Europe/Paris"):
        """window: Window length in days (left & right from current time). Has
        to be positive.
        """
        self.local_tz = self._set_local_tz(default_tz)
        self.window = window

    def _set_local_tz(self, default_tz):
        try:
            from tzlocal import get_localzone
            return get_localzone()
        except ImportError as e:
            # Change here your local timezone
            # TODO: refactor to enter default timezone via command line option
            msg = "Warning: Unable to import tzlocal, setting timezone %s"
            print_error(msg % default_tz)
            return timezone(default_tz)

    def __call__(self, fh, fh_w):
        try:
            cal = Calendar.from_ical(fh.read())
        except ValueError as e:
            msg = "ERROR parsing ical file: %s" % str(e)
            raise IcalParsingError(msg)

        now = datetime.now(utc)
        start = now - timedelta(days=self.window)
        end = now + timedelta(days=self.window)
        for comp in cal.walk():
            try:
                event_iter = generate_event_iterator(comp, start, end,
                                                     self.local_tz)
                for comp_start, comp_end, rec_event in event_iter:
                    summary = ""
                    if "SUMMARY" in comp:
                        summary = comp['SUMMARY'].to_ical()
                        summary = summary.replace('\\,', ',')
                    if not summary:
                        summary = "(No title)"
                    fh_w.write("* {}".format(summary))
                    if rec_event and self.RECUR_TAG:
                        fh_w.write(" {}\n".format(self.RECUR_TAG))
                    fh_w.write("\n")
                    if isinstance(comp["DTSTART"].dt, datetime):
                        fh_w.write("  {}--{}\n".format(
                            orgDatetime(comp_start, self.local_tz),
                            orgDatetime(comp_end, self.local_tz)))
                    else:  # all day event
                        fh_w.write("  {}--{}\n".format(
                            orgDate(comp_start, self.local_tz),
                            orgDate(
                                comp_end - timedelta(days=1), self.local_tz)))
                    if 'DESCRIPTION' in comp:
                        description = '\n'.join(
                            comp['DESCRIPTION'].to_ical().split('\\n'))
                        description = description.replace('\\,', ',')
                        fh_w.write("{}\n".format(description))

                    fh_w.write("\n")
            except Exception as e:
                msg = "Warning: an exception occured: %s" % e
                print_error(msg)

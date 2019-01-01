from __future__ import print_function
from builtins import object
import warnings
import sys
from math import floor
from datetime import date, datetime, timedelta, tzinfo
from icalendar import Calendar
from pytz import timezone, utc, all_timezones
from tzlocal import get_localzone
import click
import itertools


def orgDatetime(dt, tz):
    '''Timezone aware datetime to YYYY-MM-DD DayofWeek HH:MM str in localtime.
    '''
    return dt.astimezone(tz).strftime("<%Y-%m-%d %a %H:%M>")


def orgDate(dt, tz):
    '''Timezone aware date to YYYY-MM-DD DayofWeek in localtime.
    '''
    return dt.astimezone(tz).strftime("<%Y-%m-%d %a>")


def get_datetime(dt, tz):
    '''Convert date or datetime to local datetime.
    '''
    if isinstance(dt, datetime):
        if not dt.tzinfo:
            return dt.replace(tzinfo=tz)
        return dt
    else:
        # d is date. Being a naive date, let's suppose it is in local
        # timezone.  Unfortunately using the tzinfo argument of the standard
        # datetime constructors ''does not work'' with pytz for many
        # timezones, so create first a utc datetime, and convert to local
        # timezone
        aux_dt = datetime(year=dt.year, month=dt.month, day=dt.day, tzinfo=utc)
        return aux_dt.astimezone(tz)


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
    return (add_delta_dst(start_dt,
                          timedelta(days=delta_days * int(delta_ord))),
            int(delta_ord))


def generate_event_iterator(comp, timeframe_start, timeframe_end, tz):
    '''Get iterator with the proper delta (days, weeks, etc)'''
    # Note: timeframe_start and timeframe_end are in UTC
    if comp.name != 'VEVENT':
        return []
    if 'RRULE' in comp:
        return {
            'WEEKLY':
            EventRecurDaysIter(7, comp, timeframe_start, timeframe_end, tz),
            'DAILY':
            EventRecurDaysIter(1, comp, timeframe_start, timeframe_end, tz),
            'MONTHLY': [],
            'YEARLY':
            EventRecurYearlyIter(comp, timeframe_start, timeframe_end, tz)
        }[comp['RRULE']['FREQ'][0]]
    else:
        return EventSingleIter(comp, timeframe_start, timeframe_end, tz)


class EventSingleIter(object):
    '''Iterator for non-recurring single events.'''

    def __init__(self, comp, timeframe_start, timeframe_end, tz):
        self.ev_start = get_datetime(comp['DTSTART'].dt, tz)

        # Events with the same begin/end time same do not include
        # "DTEND".
        if "DTEND" not in comp:
            self.ev_end = self.ev_start
        else:
            self.ev_end = get_datetime(comp['DTEND'].dt, tz)

        self.duration = self.ev_end - self.ev_start
        self.result = ()
        if (self.ev_start < timeframe_end and self.ev_end > timeframe_start):
            self.result = (self.ev_start, self.ev_end, 0)

    def __iter__(self):
        return self

    # Iterate just once
    def __next__(self):
        if self.result:
            aux = self.result
            self.result = ()
        else:
            raise StopIteration
        return aux


class EventRecurDaysIter(object):
    '''Iterator for daily-based recurring events (daily, weekly).'''

    def __init__(self, days, comp, timeframe_start, timeframe_end, tz):
        self.ev_start = get_datetime(comp['DTSTART'].dt, tz)
        if "DTEND" not in comp:
            self.ev_end = self.ev_start
        else:
            self.ev_end = get_datetime(comp['DTEND'].dt, tz)
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
                                          tz).astimezone(utc)
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

        self.exclude = set()
        if 'EXDATE' in comp:
            exdate = comp['EXDATE']
            if isinstance(exdate, list):
                exdate = itertools.chain.from_iterable([e.dts for e in exdate])
            else:
                exdate = exdate.dts
            self.exclude = set([get_datetime(dt.dt, tz) for dt in exdate])

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

    def __next__(self):
        current = self.next_count() if self.is_count else self.next_until()
        while current[0] in self.exclude:
            current = self.next_count() if self.is_count else self.next_until()
        return current


class EventRecurMonthlyIter(object):
    pass


class EventRecurYearlyIter(object):
    def __init__(self, comp, timeframe_start, timeframe_end, tz):
        self.ev_start = get_datetime(comp['DTSTART'].dt, tz)
        if "DTEND" not in comp:
            self.ev_end = self.ev_start
        else:
            self.ev_end = get_datetime(comp['DTEND'].dt, tz)
        self.start = timeframe_start
        self.end = timeframe_end
        self.is_until = False
        if 'UNTIL' in comp['RRULE']:
            self.is_until = True
            self.end = min(
                self.end,
                get_datetime(comp['RRULE']['UNTIL'][0], tz).astimezone(utc))
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
        self.years = list(range(self.start.year, self.end.year + 1))
        if 'COUNT' in comp['RRULE']:
            if self.is_until:
                msg = "UNTIL and COUNT MUST NOT occur in the same 'recur'"
                raise ValueError(msg)
            self.years = list(range(self.ev_start.year, self.end.year + 1))
            del self.years[comp['RRULE']['COUNT'][0]:]
        self.i = 0
        self.n = len(self.years)

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= self.n:
            raise StopIteration
        event_aux = self.ev_start.replace(year=self.years[self.i])
        event_aux = event_aux.replace(month=self.bymonth)
        event_aux = event_aux.replace(day=self.bymonthday)
        self.i = self.i + 1
        if event_aux > self.end:
            raise StopIteration
        if event_aux < self.start:
            return next(self)
        return (event_aux,
                event_aux.tzinfo.normalize(event_aux + self.duration), 1)


class IcalParsingError(Exception):
    pass


class Convertor(object):
    RECUR_TAG = ":RECURRING:"

    # Do not change anything below

    def __init__(self, days=90, tz=None):
        """days: Window length in days (left & right from current time). Has
        to be positive.
        """
        self.tz = timezone(tz) if tz else get_localzone()
        self.days = days

    def __call__(self, fh, fh_w):
        try:
            cal = Calendar.from_ical(fh.read())
        except ValueError as e:
            msg = "ERROR parsing ical file: %s" % str(e)
            raise IcalParsingError(msg)

        now = datetime.now(utc)
        start = now - timedelta(days=self.days)
        end = now + timedelta(days=self.days)
        for comp in cal.walk():
            try:
                event_iter = generate_event_iterator(comp, start, end, self.tz)
                for comp_start, comp_end, rec_event in event_iter:
                    summary = ""
                    if "SUMMARY" in comp:
                        summary = comp['SUMMARY'].to_ical().decode("utf-8")
                        summary = summary.replace('\\,', ',')
                    location = ""
                    if "LOCATION" in comp:
                        location = comp['LOCATION'].to_ical().decode("utf-8")
                        location = location.replace('\\,', ',')
                    if not any((summary, location)):
                        summary = u"(No title)"
                    else:
                        summary += " - " + location if location else ''
                    fh_w.write(u"* {}".format(summary))
                    if rec_event and self.RECUR_TAG:
                        fh_w.write(u" {}\n".format(self.RECUR_TAG))
                    fh_w.write(u"\n")
                    if isinstance(comp["DTSTART"].dt, datetime):
                        fh_w.write(u"  {}--{}\n".format(
                            orgDatetime(comp_start, self.tz),
                            orgDatetime(comp_end, self.tz)))
                    else:  # all day event
                        fh_w.write(u"  {}--{}\n".format(
                            orgDate(comp_start, self.tz),
                            orgDate(comp_end - timedelta(days=1), self.tz)))
                    if 'DESCRIPTION' in comp:
                        description = '\n'.join(comp['DESCRIPTION'].to_ical().
                                                decode("utf-8").split('\\n'))
                        description = description.replace('\\,', ',')
                        fh_w.write(u"{}\n".format(description))

                    fh_w.write(u"\n")
            except Exception as e:
                msg = "Warning: an exception occured: %s" % e
                warnings.warn(msg)
                raise


def check_timezone(ctx, param, value):
    if (value is None) or (value in all_timezones):
        return value
    else:
        click.echo(u"Invalid timezone value {value}.".format(value=value))
        click.echo(u"Use --print-timezones to show acceptable values.")
        ctx.exit(1)


def print_timezones(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    for tz in all_timezones:
        click.echo(tz)
    ctx.exit()


@click.command(context_settings={"help_option_names": ['-h', '--help']})
@click.option(
    "--print-timezones",
    "-p",
    is_flag=True,
    callback=print_timezones,
    is_eager=True,
    expose_value=False,
    help="Print acceptable timezone names and exit.")
@click.option(
    "--days",
    "-d",
    default=90,
    type=click.IntRange(0, clamp=True),
    help=("Window length in days (left & right from current time). "
          "Has to be positive."))
@click.option(
    "--timezone",
    "-t",
    default=None,
    callback=check_timezone,
    help="Timezone to use. (local timezone by default)")
@click.argument("ics_file", type=click.File("r", encoding="utf-8"))
@click.argument("org_file", type=click.File("w", encoding="utf-8"))
def main(ics_file, org_file, days, timezone):
    """Convert ICAL format into org-mode.

    Files can be set as explicit file name, or `-` for stdin or stdout::

        $ ical2orgpy in.ical out.org

        $ ical2orgpy in.ical - > out.org

        $ cat in.ical | ical2orgpy - out.org

        $ cat in.ical | ical2orgpy - - > out.org
    """
    convertor = Convertor(days, timezone)
    try:
        convertor(ics_file, org_file)
    except IcalParsingError as e:
        click.echo(str(e), err=True)
        raise click.Abort()

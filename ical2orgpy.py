from __future__ import print_function
from builtins import object
import warnings
import sys
from dateutil.rrule import rrulestr, rruleset
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
        return EventRecur(comp, timeframe_start, timeframe_end, tz)

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


class EventRecur(object):
    '''Iterator for daily-based recurring events (daily, weekly).'''

    def __init__(self, comp, timeframe_start, timeframe_end, tz):
        self.ev_start = get_datetime(comp['DTSTART'].dt, tz)
        if "DTEND" not in comp:
            self.ev_end = self.ev_start
        else:
            self.ev_end = get_datetime(comp['DTEND'].dt, tz)
        self.duration = self.ev_end - self.ev_start

        self.recurrences = rrulestr(
            comp["RRULE"].to_ical().decode("utf-8"), dtstart=self.ev_start)
        self.rules = rruleset()
        self.rules.rrule(self.recurrences)

        self.exclude = set()
        if 'EXDATE' in comp:
            exdate = comp['EXDATE']
            if isinstance(exdate, list):
                exdate = itertools.chain.from_iterable([e.dts for e in exdate])
            else:
                exdate = exdate.dts
            self.exclude = set([get_datetime(dt.dt, tz) for dt in exdate])

            for skip in self.exclude:
                self.rules.exdate(skip)

        self.events = self.rules.between(timeframe_start, timeframe_end)

    def __iter__(self):
        return self

    def __next__(self):
        if self.events:
            current = self.events.pop()
            return (current,
                    current.tzinfo.normalize(current+self.duration),1)
        raise StopIteration


class IcalParsingError(Exception):
    pass


class Convertor(object):
    RECUR_TAG = "\t:RECURRING:"

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

        fh_w.write("".join(self.create_org_calendar(cal)))

    def create_org_calendar(self, calendar):
        now = datetime.now(utc)
        start = now - timedelta(days=self.days)
        end = now + timedelta(days=self.days)
        for comp in calendar.walk():
            try:
                yield self.create_entry(comp, start, end)
            except Exception as e:
                msg = "Warning: an exception occured: %s" % e
                warnings.warn(msg)
                raise

    def create_entry(self, comp, start, end):
        event_iter = generate_event_iterator(comp, start, end, self.tz)
        fh_w = []
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
            tag = rec_event and self.RECUR_TAG or ''
            fh_w.append(u"* {}{}\n".format(summary, tag))

            if isinstance(comp["DTSTART"].dt, datetime):
                fh_w.append(u"  {}--{}\n".format(
                    orgDatetime(comp_start, self.tz),
                    orgDatetime(comp_end, self.tz)))
            else:  # all day event
                fh_w.append(u"  {}--{}\n".format(
                    orgDate(comp_start, self.tz),
                    orgDate(comp_end - timedelta(days=1), self.tz)))
            if 'DESCRIPTION' in comp:
                description = '\n'.join(
                    comp['DESCRIPTION'].to_ical().decode("utf-8").split('\\n'))
                description = description.replace('\\,', ',')
                fh_w.append(u"{}\n".format(description))

            fh_w.append(u"\n")

        return "".join(fh_w)


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

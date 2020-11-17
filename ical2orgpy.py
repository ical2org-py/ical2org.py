from __future__ import print_function
from math import floor
from datetime import datetime, timedelta
import itertools
from icalendar import Calendar
from pytz import timezone, utc, all_timezones
from tzlocal import get_localzone
import click

def org_datetime(dt, tz):
    '''Timezone aware datetime to YYYY-MM-DD DayofWeek HH:MM str in localtime.
    '''
    return dt.astimezone(tz).strftime("<%Y-%m-%d %a %H:%M>")

def org_date(dt, tz):
    '''Timezone aware date to YYYY-MM-DD DayofWeek in localtime.
    '''
    return dt.astimezone(tz).strftime("<%Y-%m-%d %a>")

def get_datetime(dt, tz):
    '''Convert date or datetime to local datetime.
    '''
    if isinstance(dt, datetime):
        if not dt.tzinfo:
            return dt.replace(tzinfo = tz)
        return dt
    # d is date. Being a naive date, let's suppose it is in local
    # timezone.  Unfortunately using the tzinfo argument of the standard
    # datetime constructors ''does not work'' with pytz for many
    # timezones, so create first a utc datetime, and convert to local
    # timezone
    aux_dt = datetime(year=dt.year, month=dt.month, day=dt.day, tzinfo=utc)
    return aux_dt.astimezone(tz)

def add_delta_dst(dt, delta):
    '''Add a timedelta to a datetime, adjusting DST when appropriate'''
    # convert datetime to naive, add delta and convert again to its own
    # timezone
    naive_dt = dt.replace(tzinfo=None)
    return dt.tzinfo.localize(naive_dt + delta)

def advance_just_before(start_dt, timeframe_start, delta_days):
    '''Advance an start_dt datetime to the first date just before
    timeframe_start. Use delta_days for advancing the event. Precond:
    start_dt < timeframe_start'''
    delta_ord = floor(
        (timeframe_start.toordinal() - start_dt.toordinal() - 1) / delta_days)
    return (add_delta_dst(
        start_dt, timedelta(days=delta_days * int(delta_ord))), int(delta_ord))

def generate_events(comp, timeframe_start, timeframe_end, tz, emails):
    '''Get iterator with the proper delta (days, weeks, etc)'''
    # Note: timeframe_start and timeframe_end are in UTC
    if comp.name != 'VEVENT':
        return []
    if 'RRULE' in comp:
        return {
            'WEEKLY':
            DailyEvents(7, comp, timeframe_start, timeframe_end, tz, emails),
            'DAILY':
            DailyEvents(1, comp, timeframe_start, timeframe_end, tz, emails),
            'MONTHLY': [],
            'YEARLY':
            YearlyEvents(comp, timeframe_start, timeframe_end, tz, emails)
        }[comp['RRULE']['FREQ'][0]]
    return SingleEvent(comp, timeframe_start, timeframe_end, tz, emails)

def filter_events(events, comp, tz, emails):
    '''Given a set of events (datetime objects), filter out some of them according to rules in comp.
    @return remaining events
    '''
    exclude = set()
    # filter out whole event series if one attendee is in emails and his status is declined
    attL = comp.get('ATTENDEE', None)
    if attL:
        if not isinstance(attL, list):
            attL = [attL]
        for att in attL:
            if att.params.get('PARTSTAT', '') == 'DECLINED' and att.params.get('CN', '') in emails:
                return []
    if 'EXDATE' in comp:
        exdate = comp['EXDATE']
        if isinstance(exdate, list):
            exdate = itertools.chain.from_iterable([e.dts for e in exdate])
        else:
            exdate = exdate.dts
        exclude = set(get_datetime(dt.dt, tz) for dt in exdate)
    filtered_events = list()
    for ev in events:
        if ev in exclude:
            continue
        filtered_events.append(ev)
    return filtered_events

class SingleEvent():
    '''Iterator for non-recurring single events.'''

    def __init__(self, comp, timeframe_start, timeframe_end, tz, emails):
        ev_start = get_datetime(comp['DTSTART'].dt, tz)
        # Events with the same begin/end time same do not include
        # "DTEND".
        if "DTEND" not in comp:
            ev_end = ev_start
        else:
            ev_end = get_datetime(comp['DTEND'].dt, tz)
        self.duration = ev_end - ev_start
        self.events = []
        if (ev_start < timeframe_end and ev_end > timeframe_start):
            self.events = [(ev_start, ev_end, 0)
                           for ev_start in filter_events([ev_start], comp, tz, emails)]
    def __iter__(self):
        return iter(self.events)

class DailyEvents():
    '''Class for daily-based recurring events (daily, weekly).'''

    def populate(self, timeframe_start, timeframe_end):
        '''Populate all events that fall into timeframe.'''
        if self.until_utc < timeframe_start:
            return []
        self.until_utc = min(self.until_utc, timeframe_end)
        if self.ev_start < timeframe_start:
            # advance to timeframe start
            (current, counts) = advance_just_before(
                self.ev_start, timeframe_start, self.delta_days)
            if self.is_count:
                self.count -= counts
                if self.count < 1:
                    return []
            while current < timeframe_start:
                current = add_delta_dst(current, self.delta)
        else:
            current = self.ev_start
        events = []
        while current <= self.until_utc:
            events.append(current)
            current = add_delta_dst(current, self.delta)
            if self.is_count:
                self.count -= 1
                if self.count < 1:
                    break
        return events

    def __init__(self, days, comp, timeframe_start, timeframe_end, tz, emails):
        uid = comp.get('UID', '**NOID**')
        self.events = list()
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
        self.delta_days = days
        if 'INTERVAL' in comp['RRULE']:
            self.delta_days *= comp['RRULE']['INTERVAL'][0]
        self.delta = timedelta(self.delta_days)
        if 'UNTIL' in comp['RRULE']:
            if self.is_count:
                msg = "Event UID {}: UNTIL and COUNT MUST NOT occur in the same 'recur'".format(uid)
                raise ValueError(msg)
            self.until_utc = get_datetime(comp['RRULE']['UNTIL'][0],
                                          tz).astimezone(utc)
        else:
            self.until_utc = timeframe_end
        if self.until_utc < timeframe_start:
            return
        self.until_utc = min(self.until_utc, timeframe_end)
        events = self.populate(timeframe_start, timeframe_end)
        self.events = [(event, event.tzinfo.normalize(event + self.duration), 1)
                       for event in filter_events(events, comp, tz, emails)]

    def __iter__(self):
        return iter(self.events)

class MonthlyEvents():
    '''TODO: Class for monthly recurring events.'''
    pass

class YearlyEvents():
    '''Class for yearly recurring events.'''

    def __init__(self, comp, timeframe_start, timeframe_end, tz, emails):
        uid = comp.get('UID', '**NOID**')
        ev_start = get_datetime(comp['DTSTART'].dt, tz)
        if "DTEND" not in comp:
            ev_end = ev_start
        else:
            ev_end = get_datetime(comp['DTEND'].dt, tz)
        start = timeframe_start
        end = timeframe_end
        is_until = False
        if 'UNTIL' in comp['RRULE']:
            is_until = True
            end = min(end,
                      get_datetime(comp['RRULE']['UNTIL'][0],
                                   tz).astimezone(utc))
        if end < start:
            self.events = []
            return
        if 'BYMONTH' in comp['RRULE']:
            bymonth = comp['RRULE']['BYMONTH'][0]
        else:
            bymonth = ev_start.month
        if 'BYMONTHDAY' in comp['RRULE']:
            bymonthday = comp['RRULE']['BYMONTHDAY'][0]
        else:
            bymonthday = ev_start.day
        duration = ev_end - ev_start
        # populate
        years = list(range(start.year, end.year + 1))
        if 'COUNT' in comp['RRULE']:
            if is_until:
                msg = "Event UID {}: UNTIL and COUNT MUST NOT occur in the same 'recur'".format(uid)
                raise ValueError(msg)
            years = list(range(ev_start.year, end.year + 1))
            del years[comp['RRULE']['COUNT'][0]:]
        events = []
        for year in years:
            event = ev_start.replace(year=year)
            event = event.replace(month=bymonth)
            event = event.replace(day=bymonthday)
            if event > end:
                break
            if event < start:
                continue
            events.append(event)
        self.events = [(event, event.tzinfo.normalize(event + duration), 1)
                       for event in filter_events(events, comp, tz, emails)]

    def __iter__(self):
        return iter(self.events)

class IcalError(Exception):
    pass

class Convertor():
    RECUR_TAG = ":RECURRING:"

    # Do not change anything below

    def __init__(self, days=90, tz=None, emails = [], include_location=True):
        """
        days: Window length in days (left & right from current time). Has
        to be positive.
        tz: timezone. If None, use local timezone.
        emails: list of user email addresses (to deal with declined events)
        """
        self.emails = set(emails)
        self.tz = timezone(tz) if tz else get_localzone()
        self.days = days
        self.include_location = include_location

    def __call__(self, fh, fh_w):
        try:
            cal = Calendar.from_ical(fh.read())
        except ValueError as e:
            msg = "Parsing error: {}".format(e)
            raise IcalError(msg)

        now = datetime.now(utc)
        start = now - timedelta(days=self.days)
        end = now + timedelta(days=self.days)
        for comp in cal.walk():
            summary = None
            if "SUMMARY" in comp:
                summary = comp['SUMMARY'].to_ical().decode("utf-8")
                summary = summary.replace('\\,', ',')
            location = None
            if "LOCATION" in comp:
                location = comp['LOCATION'].to_ical().decode("utf-8")
                location = location.replace('\\,', ',')
            if not any((summary, location)):
                summary = u"(No title)"
            else:
                summary += " - " + location if location and self.include_location else ''
            description = None
            if 'DESCRIPTION' in comp:
                description = '\n'.join(comp['DESCRIPTION'].to_ical()
                                        .decode("utf-8").split('\\n'))
                description = description.replace('\\,', ',')
            try:
                events = generate_events(comp, start, end, self.tz, self.emails)
                for comp_start, comp_end, rec_event in events:
                    fh_w.write(u"* {}".format(summary))
                    if rec_event and self.RECUR_TAG:
                        fh_w.write(u" {}\n".format(self.RECUR_TAG))
                    fh_w.write(u"\n")
                    if isinstance(comp["DTSTART"].dt, datetime):
                        fh_w.write(u"  {}--{}\n".format(
                            org_datetime(comp_start, self.tz),
                            org_datetime(comp_end, self.tz)))
                    else:  # all day event
                        fh_w.write(u"  {}--{}\n".format(
                            org_date(comp_start, timezone('UTC')),
                            org_date(comp_end - timedelta(days=1), timezone('UTC'))))
                    if description:
                        fh_w.write(u"{}\n".format(description))
                    fh_w.write(u"\n")
            except Exception as e:
                msg = "Error: {}" .format(e)
                raise IcalError(msg)

def check_timezone(ctx, param, value):
    if (value is None) or (value in all_timezones):
        return value
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
    "--email",
    "-e",
    multiple=True,
    default=None,
    help="User email address (used to deal with declined events). You can write multiple emails with as many -e options as you like.")
@click.option(
    "--days",
    "-d",
    default=90,
    type=click.IntRange(0, clamp=True),
    help=("Window length in days (left & right from current time. Default is 90 days). "
          "Has to be positive."))
@click.option(
    "--timezone",
    "-t",
    default=None,
    callback=check_timezone,
    help="Timezone to use. (Local timezone by default).")
@click.option(
    "--location/--no-location",
    "include_location",
    default=True,
    help="Include the location (if present) in the headline. (Location is included by default).")
@click.argument("ics_file", type=click.File("r", encoding="utf-8"))
@click.argument("org_file", type=click.File("w", encoding="utf-8"))
def main(ics_file, org_file, email, days, timezone, include_location):
    """Convert ICAL format into org-mode.

    Files can be set as explicit file name, or `-` for stdin or stdout::

        $ ical2orgpy in.ical out.org

        $ ical2orgpy in.ical - > out.org

        $ cat in.ical | ical2orgpy - out.org

        $ cat in.ical | ical2orgpy - - > out.org
    """
    convertor = Convertor(days, timezone, email, include_location)
    try:
        convertor(ics_file, org_file)
    except IcalError as e:
        click.echo(str(e), err=True)
        raise click.Abort()

from __future__ import print_function

import sys
import traceback
from datetime import date, datetime, timedelta, time

import click
import recurring_ical_events
from icalendar import Calendar
from pytz import all_timezones, timezone, utc
from tzlocal import get_localzone

MIDNIGHT = time(0, 0, 0)

__version__ = "0.5"

def org_datetime(dt, tz):
    '''Timezone aware datetime to YYYY-MM-DD DayofWeek HH:MM str in localtime.
    '''
    return dt.astimezone(tz).strftime("<%Y-%m-%d %a %H:%M>")


def org_date(dt, tz):
    '''Timezone aware date to YYYY-MM-DD DayofWeek in localtime.
    '''
    if hasattr(dt, "astimezone"):
        dt = dt.astimezone(tz)
    return dt.strftime("<%Y-%m-%d %a>")


def event_is_declined(comp, emails):
    attendee_list = comp.get('ATTENDEE', None)
    if attendee_list:
        if not isinstance(attendee_list, list):
            attendee_list = [attendee_list]
        for att in attendee_list:
            if att.params.get('PARTSTAT', '') == 'DECLINED' and att.params.get('CN', '') in emails:
                return True
    return False


class IcalError(Exception):
    pass


class Convertor():
    RECUR_TAG = ":RECURRING:"

    # Do not change anything below

    def __init__(self, days=90, tz=None, emails=[], include_location=True, continue_on_error=False):
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
        self.continue_on_error = continue_on_error

    def __call__(self, ics_file, org_file):
        try:
            cal = Calendar.from_ical(ics_file.read())
        except ValueError as e:
            msg = "Parsing error: {}".format(e)
            raise IcalError(msg)

        now = datetime.now(utc)
        start = now - timedelta(days=self.days)
        end = now + timedelta(days=self.days)
        for comp in recurring_ical_events.of(
            cal, keep_recurrence_attributes=True
        ).between(start, end):
            if event_is_declined(comp, self.emails):
                continue
            try:
                org_file.write(self.create_entry(comp))
            except Exception:
                print("Exception when processing:\n", file=sys.stderr)
                print(comp.to_ical().decode('utf-8') + "\n", file=sys.stderr)
                if self.continue_on_error:
                    print(traceback.format_exc(), file=sys.stderr)
                else:
                    raise

    def create_entry(self, comp):
        output = []
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
        rec_event = "RRULE" in comp
        description = None
        if 'DESCRIPTION' in comp:
            description = '\n'.join(comp['DESCRIPTION'].to_ical()
                                    .decode("utf-8").split('\\n'))
            description = description.replace('\\,', ',')

        output.append(u"* {}".format(summary))
        if rec_event and self.RECUR_TAG:
            output.append(u" {}".format(self.RECUR_TAG))
        output.append(u"\n")

        # Get start/end/duration
        ev_start = None
        ev_end = None
        duration = None
        if "DTSTART" in comp:
            ev_start = comp["DTSTART"].dt
        if "DTEND" in comp:
            ev_end = comp["DTEND"].dt
            if ev_start is not None:
                duration = ev_end - ev_start
        elif "DURATION" in comp:
            duration = comp["DURATION"].dt
            if ev_start is not None:
                ev_end = ev_start + duration

        # Special case for some calendars that include times at midnight for
        # whole day events
        if isinstance(ev_start, datetime) and isinstance(ev_end, datetime):
            if ev_start.time() == MIDNIGHT and ev_end.time() == MIDNIGHT:
                ev_start = ev_start.date()
                ev_end = ev_end.date()

        # Format date/time appropriately
        if isinstance(ev_start, datetime):
            # Normal event with start and end
            output.append("  {}--{}\n".format(
                org_datetime(ev_start, self.tz), org_datetime(ev_end, self.tz)
                ))
        elif isinstance(ev_start, date):
            if ev_start == ev_end - timedelta(days=1):
                # single day event
                output.append("  {}\n".format(org_date(ev_start, self.tz)))
            else:
                # multiple day event
                output.append(
                    "  {}--{}\n".format(
                        org_date(ev_start, self.tz),
                        org_date(ev_end - timedelta(days=1), self.tz),
                    ))

        if description:
            output.append(u"{}\n".format(description))
        output.append(u"\n")
        return ''.join(output)


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
@click.option(
    "--continue-on-error",
    default=False,
    is_flag=True,
    help="Pass this to attempt to continue even if some events are not handled",
)
@click.argument("ics_file", type=click.File("r", encoding="utf-8"))
@click.argument("org_file", type=click.File("w", encoding="utf-8"))
@click.version_option(__version__)
def main(ics_file, org_file, email, days, timezone, include_location, continue_on_error):
    """Convert ICAL format into org-mode.

    Files can be set as explicit file name, or `-` for stdin or stdout::

        $ ical2orgpy in.ical out.org

        $ ical2orgpy in.ical - > out.org

        $ cat in.ical | ical2orgpy - out.org

        $ cat in.ical | ical2orgpy - - > out.org
    """
    convertor = Convertor(days=days, tz=timezone,
                          emails=email, include_location=include_location,
                          continue_on_error=continue_on_error)
    try:
        convertor(ics_file, org_file)
    except IcalError as e:
        click.echo(str(e), err=True)
        raise click.Abort()

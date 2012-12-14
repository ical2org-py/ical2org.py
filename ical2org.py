from math import floor
from datetime import date, datetime, timedelta
from icalendar import Calendar, Event


def canonical_date(d):
    # d can be date or datetime
    try:
        return d.replace(tzinfo=None)
    except TypeError:
        # d is date. Convert to datetime.
        dord = d.replace().toordinal()
        return datetime.fromordinal(dord)

def orgDate(dt):
    '''given a datetime, return YYYY-MM-DD DayofWeek HH:MM'''
    return dt.strftime("<%Y-%m-%d %a %H:%M>")

REC_DELTAS = { 'YEARLY' : 365,
               'WEEKLY' :  7,
               'DAILY'  :  1 }

def recurring_date(rec_start, rec_end, rec_str, interval_start, interval_end):
    
    result = []
    rec_duration = rec_end - rec_start
    rec_days = REC_DELTAS[rec_str]
    delta_ord = (interval_start.toordinal() - rec_start.toordinal()) / rec_days
    date_aux = rec_start + timedelta(days = rec_days * int(delta_ord))
    delta = timedelta(days = rec_days)
    end = interval_end
    if rec_end > interval_start and rec_end < interval_end: end = rec_end
    while date_aux < interval_start:
        date_aux += delta
    while date_aux < end:
        result.append( (date_aux, date_aux + rec_duration) )
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
        return recurring_date(comp_start, comp_end, comp['RRULE']['FREQ'][0], start, finish_date)
    if comp_start > end: return []
    if comp_end < start: return []
    return [ (comp_start, comp_end) ]

cal = Calendar.from_ical(open('basic.ics','rb').read())
#cal = Calendar.from_ical(open('kk.ics','rb').read())

now=datetime.now()
start = now - timedelta( days = +30)
end = now + timedelta( days = +30)
for comp in cal.walk():
    for comp_start, comp_end in inBetween(comp, start, end):
        print("* {}".format(comp['SUMMARY'].to_ical()))
        print("{}--{}".format(orgDate(comp_start), orgDate(comp_end)))

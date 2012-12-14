from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from icalendar import Calendar, Event

def canonical_date(d):
    # d can be date or datetime
    try:
        return d.replace(tzinfo=None)
    except TypeError:
        dord = d.replace().toordinal()
        return datetime.fromordinal(dord)

def orgDate(dt):
    '''given a datetime, return YYYY-MM-DD DayofWeek HH:MM'''
    return dt.strftime("<%Y-%m-%d %a %H:%M>")

def recurrent_dates(rec_start, rec_end, rec_str, interval_start, interval_end):
    
    result = []
    rec_deltas = { "YEARLY", 365,
                   "WEEKLY",  7,
                   "DAILY",  1)
    rec_duration = rec_end - rec_start
    delta_ord = (interval_start.toordinal() - rec_start.toordinal()) / rec_deltas[rec_str].toordinal()
    delta = timedelta(days=ceiling(delta_ord))
    end = interval_end
    if rec_end < interval_end: end = rec_end
    date_aux = rec_start
    while True:
        date_aux += delta
        if date_aux > rec_end: break
        result.append( (date_aux, date_aux + rec_duration) )
    return result

def inBetween(comp, start, end):
    '''Check whether component lies between start and end'''
    if comp.name != 'VEVENT': return []
    comp_start=canonical_date(comp['DTSTART'].dt)
    comp_end=canonical_date(comp['DTEND'].dt)
    if 'RRULE' in comp:
        # recurring event. Return true unless the event it's over
        if 'UNTIL' not in comp['RRULE']: return [ (comp_start, comp_end) ]
        # check wether finish time has passed
        finish_date = canonical_date(comp['RRULE']['UNTIL'][0])
        if finish_date < start: return []
    if comp_start > end: return []
    if comp_end < start: return []
    return [ (comp_start, comp_end) ]

cal = Calendar.from_ical(open('basic.ics','rb').read())
#cal = Calendar.from_ical(open('kk.ics','rb').read())

now=datetime.now()
start = now - relativedelta( months = +1)
end = now + relativedelta( months = +1)
for comp in cal.walk():
    for comp_start, comp_end in inBetween(comp, start, end):
        print("* {}".format(comp['SUMMARY'].to_ical()))
        print("{}--{}".format(orgDate(comp_start), orgDate(comp_end)))


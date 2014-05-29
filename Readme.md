ical2org.py
===========

This script converts an ical calendar (for instance, as exported from google
calendar) into an org-mode document. It is conceived as a replacement of the
awk script located here:

http://orgmode.org/worg/org-tutorials/org-google-sync.html

The main difference is that ical2org.py correctly manages recurring events
of "yearly", "daily" and "weekly" types. ical2org.py duplicates all
recurring events falling into a specified time-frame into the exported
org-document.

Installation
===========

ical2org.py is a python script and it needs the following libraries:

- icalendar
- pytz

You can install those packages as follows (thanks to Guido Van Hoecke):

Get iCalendar from https://pypi.python.org/pypi/icalendar, untar it and run
(you probably will also need the "python-setuptools" package)

````shell
sudo python setup.py install
````

Get pytz from https://pypi.python.org/pypi/pytz/. It comes as an egg
file so you just run 

````shell
sudo easy_install pytz-2013b-py2.7.egg
````

Customize the script
====================

You should edit the script and modify the lines at the beginning in order to
specify your local timezone (line 9) and the window of the time-frame, in
days (the time-frame is relative to the current time). You can also modify
the org TAG used for specifying that an event is recurring.

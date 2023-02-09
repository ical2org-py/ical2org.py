CHANGELOG
=========

0.5
---
* Fixed bug with whole day events with times at midnight

0.4
---
* Rewrote a lot of functionality using recurring-ical-events package
* All day events are in UTC. Fixes #42
* manage events with single attendees (closes #37)
* Manage declined events (closes #36), using ``-e``
* Added ``--continue-on-error`` flag
* Many other bug fixes

0.3
---

* Support excluding dates EXDATE (#32)
* Remove misleading info of package not being in PyPI (#31)
* Include location data, if present. Closes #30
* catch errors when end datetime of event is missing
* fix #28 by also checking datetimes for missing timezone info

0.2
---

* Add license and small fixes (mailmap)

0.1
---

* Slightly modify README to include installation from git source
* fix the "TypeError: 'range' object does not support item deletion"
* Removed import of unicode\_literals as it is discouraged (by click)
* Made py2 and py3 compatible (tested 2.7, 3.5, 3.6)
* Removed extraneous prints from testing
* Added test suite (pytest based)
* CLI by click: added --timezone, --days and --print-timezones
* Readme.md updated and renamed to README.rst. tox.ini updated
* Refactored to Convertor class
* Code reformatted, fixed some exception handling
* Print warning, if cannot import tzlocal
* Script refactored to main and convert functions
* Rewrite from script to python package
* Add GPL v3 license
* Use system timezone via  tzlocal
* Handle zero length events
* \* Proper printout of all day events
* Die gracefully if ical file is corrupt
* README: Little change in installation instructions
* ! indentations
* ! remove unnecessary escapes from SUMMARY
* Update Readme.md
* Update ical2org.py
* ! take care of unnecessary escapes and newline for DESCRIPTION
* write to the output file when provided
* Do not use EventRecurDailyIter/EventRecurWeeklyIter. Use EventRecurDaysIter instead
* fix bug
* fix little bug
* Complete rewriting of ical2org using iterators
* last day of daily repeat was being omitted
* Fix end time of recurring events
* include descriptions in the items
* Add instructions for installing dependencies
* get input from STDIN if no filename given
* Deal with yearly recurring events
* add .gitignore
* Add Readme
* put main loop under a try block
* do not crash on monthly or yearly recurring events
* Store interval time following UTC
* Fix bug. Add date normalizations where needed
* Add user-defined parameters for window and tag
* Properly deal with dates in other timezones
* do not use utc for canonical date
* Take timezones into account
* Add recurring tag to recurring events
* first version, seems to work
* init commit

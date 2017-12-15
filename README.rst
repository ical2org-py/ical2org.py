ical2orgpy
==========

This script converts an ical calendar (for instance, as exported from google
calendar) into an org-mode document. It is conceived as a replacement of the
awk script located here:

http://orgmode.org/worg/org-tutorials/org-google-sync.html

The main difference is that ical2orgpy correctly manages recurring events
of "yearly", "daily" and "weekly" types. ical2orgpy duplicates all
recurring events falling into a specified time-frame into the exported
org-document.

Installation
============

The command `ical2orgpy` is provided by means of python package `ical2orgpy`.

Use `pip` (recommended to install into virtualenv)::

    $ pip install ical2orgpy

.. info:: The package is still to be published into pypi.

Usage
=====
Simply use the `ical2orgpy` command::

    $ ical2orgpy --help

Development
===========
Clone the repository and cd into it.

Assuming you have Python 2.7 and `tox` package installed::

    $ tox -e py27

Then activate the virtualenv::

    $ source .tox/py27/bin/activate
    (py27)$

And use here the package.

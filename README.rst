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


Installing from source code
===========================

You can install the package directly from git source like this::

    $ cd <to project folder>
    $ pip install --user .

To use the script, just call::

  $ ~/.local/bin/ical2orgpy
		  
Usage
=====
Simply use the `ical2orgpy` command::

    $ ical2orgpy --help

or, if installed locally from the git repo::

    $ ~/.local/bin/ical2orgpy

.. highlight:: bash
				   
The script requires two files, the input ics and the output org
document. Usually, `ical2orgpy` is called within a script that grabs the
ical file from some source (i.e. Google Calendar), and generates the
appropriate org document. Such an script would have the following shape::

               #!/bin/bash
               
               # customize these
               WGET=<path to wget>
               ICS2ORG=<path to ical2org>
               ICSFILE=$(mktemp)
               ORGFILE=<path to orgfile>
               URL=<url to your private Google calendar>
               
               # no customization needed below
    
               $WGET -O $ICSFILE $URL
               $ICS2ORG $ICSFILE $ORGFILE
               rm -f $ICSFILE
  
See further instructions here:

http://orgmode.org/worg/org-tutorials/org-google-sync.html

Development
===========
Clone the repository and cd into it.

Assuming you have Python 2.7 and `tox` package installed::

    $ tox -e py27

Then activate the virtualenv::

    $ source .tox/py27/bin/activate
    (py27)$

And use here the package.

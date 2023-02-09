Release process
===============

* Tests: ``tox``

* Update CHANGELOG.rst, removing "(in development)" and adding date

* Update the version number in ``ical2orgpy/__init__.py``

* Commit

* Release to PyPI::

    ./release.sh

* Tag the release e.g.::

    git tag 0.5

* Update the version numbers again, moving to the next release, and adding "-dev1"

* Add new section to CHANGELOG.rst

* ``git push --tags``

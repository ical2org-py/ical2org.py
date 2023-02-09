#!/bin/sh

# Release script. See RELEASE.rst for more info

set -x

pytest || exit 1
check-manifest || exit 1

umask 000
rm -rf build dist
git ls-tree --full-tree --name-only -r HEAD | xargs chmod ugo+r

export SKIP_WRITE_GIT_CHANGELOG=1
python3 setup.py sdist || exit 1
python3 setup.py bdist_wheel --python-tag=py3 || exit 1

VERSION=$(python3 setup.py --version) || exit 1
twine upload dist/ical2orgpy-$VERSION-py3-none-any.whl dist/ical2orgpy-$VERSION.tar.gz || exit 1

#!/bin/sh

# Release script. See RELEASE.rst for more info

set -x

pytest || exit 1


umask 000
rm -rf build dist
git ls-tree --full-tree --name-only -r HEAD | xargs chmod ugo+r

export SKIP_WRITE_GIT_CHANGELOG=1
./setup.py sdist || exit 1
./setup.py bdist_wheel || exit 1

# When we switch to Python 3 only:
#python3 setup.py bdist_wheel --python-tag=py3 || exit 1

# Need to add `--version` tag
# VERSION=$(./setup.py --version) || exit 1
# twine upload dist/fluent_compiler-$VERSION.tar.gz dist/fluent_compiler-$VERSION-py3-none-any.whl || exit 1

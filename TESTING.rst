===========
How to test
===========

tox: run complete test suite
============================

Have proper Python 3 installed and have ``tox`` installed too::

    $ tox -e py39

This will create a virtualenv for Python 3.9, install into it this package, additional packages from
test_requirements.txt and run complete test suite.

pytest: testing framework
=========================
Whole test suite is using pytest_. Get familiar with it as it provides many great tools.

Test suite for this package is using parametrization.

.. _pytest: https://docs.pytest.org/en/latest/

To run test suite, you shall (assuming tox was already run) have virtualenv activated (source
.tox/py27/bin/activate), then simply::

    $ pytest -sv tests

To select particular test, use e.g.::

    $ pytest -sv tests/test_datetime.py

(see pytest_ for more methods to select only specific tests, e.g. using `-k` filter).

To debug test, use ``--pdb``, e.g.::

    $ pytest -sv tests/test_datetime.py --pdb

Hint: if you install ``pdbpp`` python package, the debugging will be more comfortable with
tab-completion (at least on Linux).

Extending parametrized tests
============================
E.g. in tests/test_datetime.py there are parametrized test, e.g.::

    @pytest.mark.parametrize(
        "dt, tz, expected", [
            (datetime(2017, 12, 15, 17, 35, 0, 0, UTC), PRAGUE,
            "<2017-12-15 Fri 18:35>"),
            (datetime(2017, 12, 15, 18, 35, 0, 0, UTC), PRAGUE,
            "<2017-12-15 Fri 19:35>"),
        ],
        ids=lambda itm: str(itm))
    def test_org_datetime(dt, tz, expected):
        res = orgDatetime(dt, tz)
        assert res == expected

Feel free to add more tests by simply adding more parameter records, e.g.::

    @pytest.mark.parametrize(
        "dt, tz, expected", [
            (datetime(2017, 12, 15, 17, 35, 0, 0, UTC), PRAGUE,
            "<2017-12-15 Fri 18:35>"),
            (datetime(2017, 12, 15, 18, 35, 0, 0, UTC), PRAGUE,
            "<2017-12-15 Fri 19:35>"),
            (datetime(2000, 12, 15, 18, 35, 0, 0, UTC), PRAGUE,
            "<2000-12-15 Fri 19:35>"),
        ],
        ids=lambda itm: str(itm))
    def test_org_datetime(dt, tz, expected):
        res = orgDatetime(dt, tz)
        assert res == expected

Creating conversion scenarios (ical -> org samples)
===================================================
There are special test scenarios for testing complete conversion::

    $ ls tests/conversions/scenarios/
    happy.ics
    happy.one.expected.org
    happy.one.yaml
    happy.two.expected.org
    happy.two.yaml

Each particular scenario consists of:

- `{main_name}.ics`: input file
- `{main_name}.{surname}.yaml`: YAML file with parameters for particular test case
- `{main_name}.{surname}.expected.org`: org file with expected result of correct conversion

One input file may serve multiple scenario (with different surnames)

Tests can be run by::

    $ pytest -sv tests/conversions/test_conversion.py
    ============================================================================================= test session starts =============================================================================================
    platform linux2 -- Python 2.7.13, pytest-3.3.1, py-1.5.2, pluggy-0.6.0 -- /home/javl/sandbox/ical2org.py/.tox/py27/bin/python2.7
    cachedir: .cache
    rootdir: /home/javl/sandbox/ical2org.py, inifile:
    collected 2 items

    tests/conversions/test_conversion.py::test_conversion[happy.two] PASSED                                                                                                                                 [ 50%]
    tests/conversions/test_conversion.py::test_conversion[happy.one] PASSED                                                                                                                                 [100%]

    ========================================================================================== 2 passed in 0.22 seconds ===========================================================================================

If you add more scenario files, more tests will be run.

Magic with freezegun (changing current time)
============================================
As the conversion generates different results for different moments in time (as there is number of
days which are taken into account, by default 90 days back and forward), time affects generated
results. Using great package freezegun_, this is possible. YAML file defines date time for the test
to run and Scenario class provides method freezing the time to given moment.

To play with the scenarios, there is no need to touch python code, it is enough to provide new files
for new scenarios.

.. _freezegun:: https://github.com/spulec/freezegun

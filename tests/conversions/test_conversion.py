from datetime import datetime
import pytest
from py.path import local
import yaml
from freezegun import freeze_time
from pytz import timezone

from ical2orgpy import Convertor

FILEROOT = local("tests/conversions/scenarios")

assert FILEROOT.exists()


class Scenario(object):
    @classmethod
    def discover(cls, fileroot):
        return [Scenario(cfgfile) for cfgfile in fileroot.listdir("*.yaml")]

    def __init__(self, cfg_file):
        self.cfg_file = cfg_file
        self.fileroot = cfg_file.dirpath()
        """directory where are all the scenarios"""

        self.name = cfg_file.purebasename
        ics_purebasename = self.name.rsplit(".", 1)[0]
        self.ics_file = cfg_file.new(purebasename=ics_purebasename, ext=".ics")
        """ICS file serving as conversion input"""

        assert self.ics_file, "ICS file exists"

        self.expected_file = cfg_file.new(ext=".expected.org")
        """Expected result of conversion to org format"""
        assert self.expected_file.exists()

        with cfg_file.open("r", encoding="utf-8") as f:
            self.cfg = yaml.load(f, Loader=yaml.FullLoader)

        self.desciption = self.cfg["description"]
        """Test case description"""

        # YAML converts ctime to datetime
        self.context = self.cfg["context"]

        # no conversions here
        self.parameters = self.cfg["parameters"]

    def freeze_time(self):
        """Provide context manager mocking context time from scenario.

        Using freezegun utility, it temporarily provide different
        "now" time for datetime based functions.
        """
        ctime = self.context["ctime"]
        tz = timezone(self.context["tzone"])
        is_dst = self.context.get("is_dst", False)
        offset = tz.utcoffset(ctime, is_dst=is_dst).total_seconds()
        return freeze_time(ctime, tz_offset=offset / 3600)


SCENARIOS = Scenario.discover(FILEROOT)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda itm: itm.name)
def test_conversion(scenario, tmpdir):
    cfg_file = tmpdir / "cfg_file.yaml"
    ics_file = tmpdir / "input.ics"
    expected_file = tmpdir / "expected.org"

    # copy files from scenario into tmpdir
    # it shall make researching problems simpler
    scenario.cfg_file.copy(cfg_file)
    scenario.ics_file.copy(ics_file)
    scenario.expected_file.copy(expected_file)

    assert cfg_file.exists()
    assert ics_file.exists()
    assert expected_file.exists()

    convertor = Convertor(scenario.parameters["days"],
                          scenario.parameters["tzone"])

    result_file = tmpdir / "output.org"
    with scenario.freeze_time():
        with ics_file.open("r", encoding="utf-8") as ics_f:
            with result_file.open("w", encoding="utf-8") as result_f:
                convertor(ics_f, result_f)
    assert result_file.exists()
    res_txt = result_file.read_text(encoding="utf-8")
    exp_txt = expected_file.read_text(encoding="utf-8")
    assert res_txt == exp_txt

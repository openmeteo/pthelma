from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys
import tempfile
import textwrap
from io import StringIO
from typing import Any, Dict, List
from unittest import TestCase, skipUnless
from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner, Result

from enhydris_api_client import EnhydrisApiClient
from enhydris_cache import cli
from htimeseries import HTimeseries


class NonExistentConfigFileTestCase(TestCase):
    def setUp(self) -> None:
        runner = CliRunner(mix_stderr=False)
        self.result: Result = runner.invoke(cli.main, ["nonexistent.conf"])

    def test_exit_status(self) -> None:
        self.assertEqual(self.result.exit_code, 1)

    def test_error_message(self) -> None:
        self.assertIn(
            "No such file or directory: 'nonexistent.conf'", self.result.stderr
        )


class ConfigurationTestCase(TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp()
        self.configfilename = os.path.join(self.tempdir, "enhydris-cache.conf")

    def tearDown(self) -> None:
        shutil.rmtree(self.tempdir)

    def test_nonexistent_log_level_raises_error(self) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = HELLO
                    """
                )
            )
        msg = "loglevel must be one of ERROR, WARNING, INFO, DEBUG"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_base_url_parameter_raises_error(self) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = WARNING

                    [Temperature]
                    station_id = 585
                    timeseries_group_id = 5858
                    timeseries_id = 58585
                    file = /tmp/temperature.hts
                    """
                )
            )
        msg = "No option 'base_url'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_station_id_parameter_raises_error(self) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = WARNING

                    [Temperature]
                    base_url = https://openmeteo.org/
                    timeseries_group_id = 5858
                    timeseries_id = 58585
                    file = /tmp/temperature.hts
                    """
                )
            )
        msg = "No option 'station_id'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_timeseries_group_id_parameter_raises_error(self) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = WARNING

                    [Temperature]
                    base_url = https://openmeteo.org/
                    station_id = 585
                    timeseries_id = 58585
                    file = /tmp/temperature.hts
                    """
                )
            )
        msg = "No option 'timeseries_group_id'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_timeseries_id_parameter_raises_error(self) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = WARNING

                    [Temperature]
                    base_url = https://openmeteo.org/
                    station_id = 585
                    timeseries_group_id = 5858
                    file = /tmp/temperature.hts
                    """
                )
            )
        msg = "No option 'timeseries_id'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_file_parameter_raises_error(self) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = WARNING

                    [Temperature]
                    base_url = https://openmeteo.org/
                    station_id = 585
                    timeseries_group_id = 5858
                    timeseries_id = 58585
                    """
                )
            )
        msg = "No option 'file'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_wrong_station_id_parameter_raises_error(self) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = WARNING

                    [Temperature]
                    base_url = https://openmeteo.org/
                    station_id = hello
                    timeseries_group_id = 5858
                    timeseries_id = 58585
                    file = /tmp/temperature.hts
                    """
                )
            )
        with self.assertRaisesRegex(click.ClickException, "not a valid integer"):
            cli.App(self.configfilename).run()

    def test_wrong_timeseries_group_id_parameter_raises_error(self) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = WARNING

                    [Temperature]
                    base_url = https://openmeteo.org/
                    station_id = 585
                    timeseries_group_id = hello
                    timeseries_id = 58585
                    file = /tmp/temperature.hts
                    """
                )
            )
        with self.assertRaisesRegex(click.ClickException, "not a valid integer"):
            cli.App(self.configfilename).run()

    def test_wrong_timeseries_id_parameter_raises_error(self) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = WARNING

                    [Temperature]
                    base_url = https://openmeteo.org/
                    station_id = 585
                    timeseries_group_id = 5858
                    timeseries_id = hello
                    file = /tmp/temperature.hts
                    """
                )
            )
        with self.assertRaisesRegex(click.ClickException, "not a valid integer"):
            cli.App(self.configfilename).run()

    @patch("enhydris_cache.cli.App._execute")
    def test_correct_configuration_executes(self, m: MagicMock) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = WARNING

                    [Temperature]
                    base_url = https://openmeteo.org/
                    station_id = 585
                    timeseries_group_id = 5850
                    timeseries_id = 58505
                    file = /tmp/temperature.hts
                    """
            )
        cli.App(self.configfilename).run()
        m.assert_called_once_with()

    @patch("enhydris_cache.cli.App._execute")
    def test_missing_auth_token_makes_it_none(self, m: MagicMock) -> None:
        with open(self.configfilename, "w") as f:
            f.write(
                f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = WARNING

                    [Temperature]
                    base_url = https://openmeteo.org/
                    station_id = 585
                    timeseries_group_id = 5850
                    timeseries_id = 58505
                    file = /tmp/temperature.hts
                    """
            )
        app = cli.App(self.configfilename)
        app.run()
        assert app.config is not None
        self.assertIsNone(app.config.timeseries_group[0]["auth_token"])

    @patch("enhydris_cache.cli.App._execute")
    def test_creates_log_file(self, *mock_objects: MagicMock) -> None:
        logfilename = os.path.join(self.tempdir, "enhydris_cache.log")
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {logfilename}
                    loglevel = WARNING

                    [Temperature]
                    base_url = https://openmeteo.org/
                    station_id = 585
                    timeseries_group_id = 5850
                    timeseries_id = 58505
                    file = /tmp/temperature.hts
                    """
                )
            )
        cli.App(self.configfilename).run()
        self.assertTrue(os.path.exists(logfilename))


UTC_PLUS_2 = dt.timezone(dt.timedelta(hours=2))


@skipUnless(
    os.getenv("PTHELMA_TEST_ENHYDRIS_SERVER"), "set PTHELMA_TEST_ENHYDRIS_SERVER"
)
class EnhydrisCacheE2eTestCase(TestCase):
    """For details and warning about the PTHELMA_TEST_ENHYDRIS_SERVER environment
    variable, see tests/enhydris_api_client/test_e2e.py.
    """

    test_timeseries1 = textwrap.dedent(
        """\
        2014-01-01 08:00,11.0,
        2014-01-02 08:00,12.0,
        2014-01-03 08:00,13.0,
        2014-01-04 08:00,14.0,
        2014-01-05 08:00,15.0,
        """
    )
    test_timeseries2 = textwrap.dedent(
        """\
        2014-07-01 08:00,9.1,
        2014-07-02 08:00,9.2,
        2014-07-03 08:00,9.3,
        2014-07-04 08:00,9.4,
        2014-07-05 08:00,9.5,
        """
    )
    timeseries1_top = "".join(test_timeseries1.splitlines(True)[:-1])
    timeseries2_top = "".join(test_timeseries2.splitlines(True)[:-1])
    timeseries1_bottom = test_timeseries1.splitlines(True)[-1]
    timeseries2_bottom = test_timeseries2.splitlines(True)[-1]

    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.tempdir, "enhydris_cache.conf")
        self.saved_argv: List[str] = sys.argv
        sys.argv = ["enhydris_cache", "--traceback", self.config_file]
        self.savedcwd = os.getcwd()

        # Create two stations, each one with a time series
        raw_parameters = os.getenv("PTHELMA_TEST_ENHYDRIS_SERVER")
        assert raw_parameters is not None
        self.parms: Dict[str, Any] = json.loads(raw_parameters)
        self.station_id = self.parms["station_id"]
        self.timeseries_group_id = self.parms["timeseries_group_id"]
        self.api_client = EnhydrisApiClient(
            self.parms["base_url"], token=self.parms["token"]
        )
        self.api_client.__enter__()
        with self.api_client:
            self.timeseries1_id = self.api_client.post_timeseries(
                self.station_id,
                self.timeseries_group_id,
                {
                    "timeseries_group": self.timeseries_group_id,
                    "type": "Aggregated",
                    "time_step": "30min",
                },
            )
            self.timeseries2_id = self.api_client.post_timeseries(
                self.station_id,
                self.timeseries_group_id,
                {
                    "timeseries_group": self.timeseries_group_id,
                    "type": "Aggregated",
                    "time_step": "2H",
                },
            )

        # Add some data (all but the last record) to the database
        self.api_client.post_tsdata(
            self.station_id,
            self.timeseries_group_id,
            self.timeseries1_id,
            HTimeseries(StringIO(self.timeseries1_top), default_tzinfo=UTC_PLUS_2),
        )
        self.api_client.post_tsdata(
            self.station_id,
            self.timeseries_group_id,
            self.timeseries2_id,
            HTimeseries(StringIO(self.timeseries2_top), default_tzinfo=UTC_PLUS_2),
        )

        # Prepare a configuration file (some tests override it)
        with open(self.config_file, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    [General]
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    cache_dir = {self.tempdir}

                    [timeseries1]
                    base_url = {self.parms["base_url"]}
                    station_id = {self.station_id}
                    timeseries_group_id = {self.timeseries_group_id}
                    timeseries_id = {self.timeseries1_id}
                    file = file1
                    auth_token = {self.parms["token"]}

                    [timeseries2]
                    base_url = {self.parms["base_url"]}
                    station_id = {self.station_id}
                    timeseries_group_id = {self.timeseries_group_id}
                    timeseries_id = {self.timeseries2_id}
                    file = file2
                    auth_token = {self.parms["token"]}
                    """
                )
            )

    def tearDown(self) -> None:
        self.api_client.delete_timeseries(
            self.station_id, self.timeseries_group_id, self.timeseries2_id
        )
        self.api_client.delete_timeseries(
            self.station_id, self.timeseries_group_id, self.timeseries1_id
        )
        os.chdir(self.savedcwd)
        shutil.rmtree(self.tempdir)
        sys.argv = self.saved_argv
        self.api_client.__exit__()

    def test_execute(self) -> None:
        application = cli.App(self.config_file)

        # Check that the two files don't exist yet
        self.assertFalse(os.path.exists(os.path.join(self.tempdir, "file1")))
        self.assertFalse(os.path.exists(os.path.join(self.tempdir, "file2")))

        # Execute the application
        application.run()

        # Check that it has created two files
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, "file1")))
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, "file2")))

        # Check that the files are what they should be
        with open("file1", newline="\n") as f:
            ts1_before = HTimeseries(f)
        self.assertEqual(ts1_before.time_step, "30min")
        c = StringIO()
        ts1_before.write(c)
        self.assertEqual(c.getvalue().replace("\r", ""), self.timeseries1_top)
        with open("file2", newline="\n") as f:
            ts2_before = HTimeseries(f)
        self.assertEqual(ts2_before.time_step, "2H")
        c = StringIO()
        ts2_before.write(c)
        self.assertEqual(c.getvalue().replace("\r", ""), self.timeseries2_top)

        # Append a record to the database for each timeseries
        self.api_client.post_tsdata(
            self.station_id,
            self.timeseries_group_id,
            self.timeseries1_id,
            HTimeseries(StringIO(self.timeseries1_bottom), default_tzinfo=UTC_PLUS_2),
        )
        self.api_client.post_tsdata(
            self.station_id,
            self.timeseries_group_id,
            self.timeseries2_id,
            HTimeseries(StringIO(self.timeseries2_bottom), default_tzinfo=UTC_PLUS_2),
        )

        # Execute the application again
        application.run()

        # Check that the files are what they should be
        with open("file1", newline="\n") as f:
            ts1_after = HTimeseries(f)
        self.assertEqual(ts1_after.time_step, "30min")
        c = StringIO()
        ts1_after.write(c)
        self.assertEqual(c.getvalue().replace("\r", ""), self.test_timeseries1)
        with open("file2", newline="\n") as f:
            ts2_after = HTimeseries(f)
        self.assertEqual(ts2_after.time_step, "2H")
        c = StringIO()
        ts2_after.write(c)
        self.assertEqual(c.getvalue().replace("\r", ""), self.test_timeseries2)

        # Check that the time series comments are the same before and after
        self.assertEqual(ts1_before.comment, ts1_after.comment)
        self.assertEqual(ts2_before.comment, ts2_after.comment)

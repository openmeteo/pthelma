import datetime as dt
import os
import shutil
import tempfile
import textwrap
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import click
from click.testing import CliRunner
from osgeo import gdal, osr

from hspatial import cli
from htimeseries import TzinfoFromString

gdal.UseExceptions()


def create_geotiff_file(filename, value):
    geo_transform = (-16.25, 1.0, 0, 16.217, 0, 1.0)
    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    f = gdal.GetDriverByName("GTiff").Create(filename, 2, 1, 1, gdal.GDT_Float32)
    try:
        f.SetGeoTransform(geo_transform)
        f.SetProjection(wgs84.ExportToWkt())
        f.GetRasterBand(1).WriteArray(value)
    finally:
        # Close the dataset
        f = None


class NonExistentConfigFileTestCase(TestCase):
    def setUp(self):
        runner = CliRunner(mix_stderr=False)
        self.result = runner.invoke(cli.main, ["nonexistent.conf"])

    def test_exit_status(self):
        self.assertEqual(self.result.exit_code, 1)

    def test_error_message(self):
        self.assertIn(
            "No such file or directory: 'nonexistent.conf'", self.result.stderr
        )


class ConfigurationTestCase(TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.configfilename = os.path.join(self.tempdir, "hspatial.conf")

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_missing_mask_parameter_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    epsg = 2100
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    number_of_output_files = 24
                    method = idw
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        msg = "No option 'mask'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_nonexistent_log_level_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    loglevel = HELLO
                    mask = /etc/hspatial/mask.tif
                    epsg = 2100
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    number_of_output_files = 24
                    method = idw
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        msg = "loglevel must be one of ERROR, WARNING, INFO, DEBUG"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_epsg_parameter_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = /etc/hspatial/mask.tif
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    number_of_output_files = 24
                    method = idw
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        msg = "No option 'epsg'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_wrong_epsg_parameter_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = /etc/hspatial/mask.tif
                    epsg = hello
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    number_of_output_files = 24
                    method = idw
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        msg = 'Option "epsg" must be an integer'
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_filename_prefix_parameter_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = /etc/hspatial/mask.tif
                    epsg = 2100
                    output_dir = /var/opt/hspatial
                    number_of_output_files = 24
                    method = idw
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        msg = "No option 'filename_prefix'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_output_dir_parameter_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = /etc/hspatial/mask.tif
                    epsg = 2100
                    filename_prefix = rainfall
                    number_of_output_files = 24
                    method = idw
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        msg = "No option 'output_dir'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_number_of_output_files_parameter_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = /etc/hspatial/mask.tif
                    epsg = 2100
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    method = idw
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        msg = "No option 'number_of_output_files'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_wrong_number_of_output_files_parameter_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = /etc/hspatial/mask.tif
                    epsg = 2100
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    method = idw
                    number_of_output_files = hello
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        msg = 'Option "number_of_output_files" must be an integer'
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_method_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = /etc/hspatial/mask.tif
                    epsg = 2100
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    number_of_output_files = 24
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        msg = "No option 'method'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_missing_files_parameter_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = /etc/hspatial/mask.tif
                    epsg = 2100
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    method = idw
                    number_of_output_files = 24
                    """
                )
            )
        msg = "No option 'files'"
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    def test_wrong_alpha_parameter_raises_error(self):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = /etc/hspatial/mask.tif
                    epsg = 2100
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    method = idw
                    number_of_output_files = 24
                    alpha = hello
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        msg = 'Option "alpha" must be a number'
        with self.assertRaisesRegex(click.ClickException, msg):
            cli.App(self.configfilename).run()

    @patch("hspatial.cli.App._execute")
    def test_correct_configuration_executes(self, m):
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = /etc/hspatial/mask.tif
                    epsg = 2100
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    method = idw
                    number_of_output_files = 24
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        cli.App(self.configfilename).run()
        m.assert_called_once_with()

    @patch("hspatial.cli.App._execute")
    def test_creates_log_file(self, *args):
        logfilename = os.path.join(self.tempdir, "hspatial.log")
        with open(self.configfilename, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {logfilename}
                    mask = /etc/hspatial/mask.tif
                    epsg = 2100
                    output_dir = /var/opt/hspatial
                    filename_prefix = rainfall
                    method = idw
                    number_of_output_files = 24
                    files = /var/opt/timeseries/inputfile1.hts
                            /var/opt/timeseries/inputfile2.hts
                            /var/opt/timeseries/inputfile3.hts
                    """
                )
            )
        cli.App(self.configfilename).run()
        self.assertTrue(os.path.exists(logfilename))


def _create_test_data(filename1, filename2):
    with open(filename1, "w") as f:
        f.write(
            textwrap.dedent(
                """\
                Location=23.78743 37.97385 4326
                Timezone=+0200
                Time_step=60,0

                2014-04-30 11:00,18.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                2014-04-30 15:00,22.4,
                """
            )
        )
    with open(filename2, "w") as f:
        f.write(
            textwrap.dedent(
                """\
                Location=24.56789 38.76543 4326
                Timezone=EET (+0200)
                Time_step=60,0

                2014-04-30 11:00,18.3,
                2014-04-30 12:00,19.3,
                2014-04-30 13:00,20.4,
                2014-04-30 14:00,21.4,
                """
            )
        )


class AppTestCase(TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.tempdir, "output")
        self.config_file = os.path.join(self.tempdir, "spatialize.conf")
        os.mkdir(self.output_dir)
        self.mask_file = os.path.join(self.tempdir, "mask.tif")
        self.filenames = [os.path.join(self.tempdir, x) for x in ("ts1", "ts2")]
        _create_test_data(self.filenames[0], self.filenames[1])
        self._prepare_config_file()

    def _prepare_config_file(self, number_of_output_files=24):
        with open(self.config_file, "w") as f:
            f.write(
                textwrap.dedent(
                    f"""\
                    logfile = {os.path.join(self.tempdir, "logfile")}
                    mask = {self.mask_file}
                    epsg = 2100
                    output_dir = {self.output_dir}
                    filename_prefix = rainfall
                    number_of_output_files = {number_of_output_files}
                    method = idw
                    files = {self.filenames[0]}
                            {self.filenames[1]}
                    """
                )
            )

    def _create_mask_file(self):
        mask_filename = os.path.join(self.tempdir, "mask.tif")
        mask = gdal.GetDriverByName("GTiff").Create(
            mask_filename, 640, 480, 1, gdal.GDT_Float32
        )
        mask.SetGeoTransform((23, 0.01, 0, 39, 0, -0.01))
        mask.SetProjection(
            'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,'
            '298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"'
            ']],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",'
            '0.01745329251994328,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG",'
            '"4326"]]'
        )
        mask = None

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_get_last_dates(self):
        application = cli.App(self.config_file)
        tzinfo = TzinfoFromString("+0200")
        self.assertEqual(
            application._get_last_dates(self.filenames[0], 2),
            [
                dt.datetime(2014, 4, 30, 14, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 15, 0, tzinfo=tzinfo),
            ],
        )
        self.assertEqual(
            application._get_last_dates(self.filenames[0], 20),
            [
                dt.datetime(2014, 4, 30, 11, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 13, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 14, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 15, 0, tzinfo=tzinfo),
            ],
        )

    @patch("hspatial.cli.App._execute")
    def test_dates_to_calculate(self, *args):
        application = cli.App(self.config_file)
        application.run()
        tzinfo = TzinfoFromString("+0200")

        # Check for number_of_output_files=24
        dates = []
        for d in application._dates_to_calculate:
            dates.append(d)
        self.assertEqual(
            dates,
            [
                dt.datetime(2014, 4, 30, 11, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 12, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 13, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 14, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 15, 0, tzinfo=tzinfo),
            ],
        )

        # Check for number_of_output_files=2
        application.config.number_of_output_files = 2
        dates = []
        for d in application._dates_to_calculate:
            dates.append(d)
        self.assertEqual(
            dates,
            [
                dt.datetime(2014, 4, 30, 14, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 15, 0, tzinfo=tzinfo),
            ],
        )

        # Check for number_of_output_files=4
        application.config.number_of_output_files = 4
        dates = []
        for d in application._dates_to_calculate:
            dates.append(d)
        self.assertEqual(
            dates,
            [
                dt.datetime(2014, 4, 30, 12, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 13, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 14, 0, tzinfo=tzinfo),
                dt.datetime(2014, 4, 30, 15, 0, tzinfo=tzinfo),
            ],
        )

    def test_dates_to_calculate_error1(self):
        self._create_mask_file()
        application = cli.App(self.config_file)
        with open(self.filenames[0], "a") as f:
            f.write(
                textwrap.dedent(
                    """\
                    2014-04-30 16:00,23.4,
                    malformed date,24.4,
                    2014-04-30 18:00,25.4,
                    2014-04-30 19:00,25.4,
                    """
                )
            )
        msg = (
            r"^Unable to parse date string u?'malformed date' "
            r"\(file " + self.filenames[0] + r", 3 lines from the end\)$"
        )
        with self.assertRaisesRegex(click.ClickException, msg):
            application.run()

    @patch("hspatial.cli.App._execute")
    def test_date_fmt(self, m):
        application = cli.App(self.config_file)
        application.run()

        # Ten-minute
        with open(self.filenames[0], "w") as f:
            f.write("Time_step=10min\n\n")
        with open(self.filenames[1], "w") as f:
            f.write("Time_step=10min\n\n")
        self.assertEqual(application._date_fmt, "%Y-%m-%d %H:%M%z")

        # Hourly
        with open(self.filenames[0], "w") as f:
            f.write("Time_step=h\n\n")
        with open(self.filenames[1], "w") as f:
            f.write("Time_step=h\n\n")
        self.assertEqual(application._date_fmt, "%Y-%m-%d %H:%M%z")

        # Daily
        with open(self.filenames[0], "w") as f:
            f.write("Time_step=D\n\n")
        with open(self.filenames[1], "w") as f:
            f.write("Time_step=D\n\n")
        self.assertEqual(application._date_fmt, "%Y-%m-%d")

        # Monthly
        with open(self.filenames[0], "w") as f:
            f.write("Time_step=M\n\n")
        with open(self.filenames[1], "w") as f:
            f.write("Time_step=M\n\n")
        self.assertEqual(application._date_fmt, "%Y-%m")

        # Annual
        with open(self.filenames[0], "w") as f:
            f.write("Time_step=Y\n\n")
        with open(self.filenames[1], "w") as f:
            f.write("Time_step=Y\n\n")
        self.assertEqual(application._date_fmt, "%Y")

        # Inconsistent
        with open(self.filenames[0], "w") as f:
            f.write("Time_step=10min\n\n")
        with open(self.filenames[1], "w") as f:
            f.write("Time_step=60min\n\n")
        with self.assertRaises(click.ClickException):
            application._date_fmt

    @patch("hspatial.cli.App._execute")
    def test_delete_obsolete_files(self, m):
        application = cli.App(self.config_file)
        application.run()

        # Create three files
        prefix = application.config.filename_prefix
        filename1 = os.path.join(self.output_dir, "{}-1.tif".format(prefix))
        filename2 = os.path.join(self.output_dir, "{}-2.tif".format(prefix))
        filename3 = os.path.join(self.output_dir, "{}-3.tif".format(prefix))
        Path(filename1).touch()
        Path(filename2).touch()
        Path(filename3).touch()

        # Just to make sure we didn't screw up above, check
        self.assertTrue(os.path.exists(filename1))
        self.assertTrue(os.path.exists(filename2))
        self.assertTrue(os.path.exists(filename3))

        # Execute for number_of_output_files = 2 and check
        application.config.number_of_output_files = 2
        application._delete_obsolete_files()
        self.assertFalse(os.path.exists(filename1))
        self.assertTrue(os.path.exists(filename2))
        self.assertTrue(os.path.exists(filename3))

        # Re-execute; nothing should have changed
        application._delete_obsolete_files()
        self.assertFalse(os.path.exists(filename1))
        self.assertTrue(os.path.exists(filename2))
        self.assertTrue(os.path.exists(filename3))

    def test_run(self):
        application = cli.App(self.config_file)

        # Create a mask
        self._create_mask_file()

        # Execute
        self._prepare_config_file(number_of_output_files=3)
        application.run()

        # Check that it has created three files
        full_prefix = os.path.join(self.output_dir, application.config.filename_prefix)
        self.assertTrue(os.path.exists(full_prefix + "-2014-04-30-15-00+0200.tif"))
        self.assertTrue(os.path.exists(full_prefix + "-2014-04-30-14-00+0200.tif"))
        self.assertTrue(os.path.exists(full_prefix + "-2014-04-30-13-00+0200.tif"))

        # Check the timestamp in the last file
        fp = gdal.Open(full_prefix + "-2014-04-30-15-00+0200.tif")
        timestamp = fp.GetMetadata()["TIMESTAMP"]
        fp = None
        self.assertEqual(timestamp, "2014-04-30 15:00+0200")

        # We could check a myriad other things here, but since we've
        # unit-tested lower level functions in detail, the above is reasonably
        # sufficient for us to know that it works.

    def test_no_timezone(self):
        self._remove_timezone_from_file(self.filenames[0])
        self._remove_timezone_from_file(self.filenames[1])
        application = cli.App(self.config_file)
        self._create_mask_file()
        self._prepare_config_file(number_of_output_files=3)
        msg = "{} does not contain Timezone".format(self.filenames[0])
        with self.assertRaisesRegex(click.ClickException, msg):
            application.run()

    def _remove_timezone_from_file(self, filename):
        with open(filename, "r") as f:
            lines = f.readlines()
        with open(filename, "w") as f:
            for line in lines:
                if not line.startswith("Timezone="):
                    f.write(line)

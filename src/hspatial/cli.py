import configparser
import datetime as dt
import logging
import os
import traceback
from glob import glob
from io import StringIO

import click
import iso8601
from osgeo import gdal, ogr, osr
from simpletail import ropen

from hspatial import create_ogr_layer_from_timeseries, h_integrate, idw
from htimeseries import HTimeseries, TzinfoFromString
from pthelma._version import __version__

gdal.UseExceptions()


class WrongValueError(configparser.Error):
    pass


class App:
    def __init__(self, configfilename):
        self.configfilename = configfilename

    def run(self):
        self.config = AppConfig(self.configfilename)
        self.config.read()
        self._setup_logger()
        self._execute_with_error_handling()

    def _execute_with_error_handling(self):
        self.logger.info("Starting spatialize, " + dt.datetime.today().isoformat())
        try:
            self._execute()
        except Exception as e:
            self.logger.error(str(e))
            self.logger.debug(traceback.format_exc())
            self.logger.info(
                "spatialize terminated with error, " + dt.datetime.today().isoformat()
            )
            raise click.ClickException(str(e))
        else:
            self.logger.info("Finished spatialize, " + dt.datetime.today().isoformat())

    def _setup_logger(self):
        self.logger = logging.getLogger("spatialize")
        self._set_logger_handler()
        self.logger.setLevel(self.config.loglevel.upper())

    def _set_logger_handler(self):
        if getattr(self.config, "logfile", None):
            self.logger.addHandler(logging.FileHandler(self.config.logfile))
        else:
            self.logger.addHandler(logging.StreamHandler())

    def _get_last_dates(self, filename, n):
        """
        Assuming specified file contains a time series, scan it from the bottom
        and return the list of the n last dates (may be less than n if the time
        series is too small). 'filename' is used in error messages.
        """
        # Get the time zone
        with open(filename) as fp:
            for line in fp:
                if line.startswith("Timezone") or (line and line[0] in "0123456789"):
                    break
        if not line.startswith("Timezone"):
            raise click.ClickException("{} does not contain Timezone".format(filename))
        zonestr = line.partition("=")[2].strip()
        timezone = TzinfoFromString(zonestr)

        result = []
        previous_line_was_empty = False
        with ropen(filename) as fp:
            for i, line in enumerate(fp):
                if i >= n:
                    break
                line = line.strip()

                # Ignore empty lines
                if not line:
                    previous_line_was_empty = True
                    continue

                # Is the line in the form of an ini file configuration line?
                items = line.split("=")
                if len(items) and ("," not in items[0]) and previous_line_was_empty:
                    break  # Yes; we reached the start of the file

                previous_line_was_empty = False

                datestring = line.split(",")[0]
                try:
                    result.insert(
                        0, iso8601.parse_date(datestring, default_timezone=timezone)
                    )
                except iso8601.ParseError as e:
                    raise click.ClickException(
                        str(e)
                        + " (file {}, {} lines from the end)".format(filename, i + 1)
                    )
        return result

    @property
    def _dates_to_calculate(self):
        """
        Generator that yields the dates for which h_integrate should be run;
        this is the latest list of dates such that:
        * At least one of the time series has data
        * The length of the list is the 'number_of_output_files' configuration
          option (maybe less if the time series don't have enough data yet).
        """
        n = self.config.number_of_output_files
        dates = set()
        for filename in self.config.files:
            dates |= set(self._get_last_dates(filename, n))
        dates = list(dates)
        dates.sort()
        dates = dates[-n:]
        for d in dates:
            yield d

    @property
    def _time_step(self):
        """
        Return time step of all time series. If time step is not the same
        for all time series, raises exception.
        """
        time_step = None
        for filename in self.config.files:
            with open(filename, newline="\n") as f:
                t = HTimeseries(f, start_date="0001-01-01 00:00")
            item_time_step = t.time_step
            if time_step and (item_time_step != time_step):
                raise click.ClickException("Not all time series have the same step")
            time_step = item_time_step
        return time_step

    @property
    def _date_fmt(self):
        """
        Determine date_fmt based on time series time step.
        """
        if self._time_step.endswith("min") or self._time_step.endswith("h"):
            return "%Y-%m-%d %H:%M%z"
        elif self._time_step.endswith("D"):
            return "%Y-%m-%d"
        elif self._time_step.endswith("M"):
            return "%Y-%m"
        elif self._time_step.endswith("Y"):
            return "%Y"
        raise click.ClickException("Can't use time step " + str(self._time_step))

    def _delete_obsolete_files(self):
        """
        Delete all tif files produced in the past except the last N,
        where N is the 'number_of_output_files' configuration option.
        """
        pattern = os.path.join(
            self.config.output_dir, "{}-*.tif".format(self.config.filename_prefix)
        )
        files = glob(pattern)
        files.sort()
        for filename in files[: -self.config.number_of_output_files]:
            os.remove(filename)

    def _execute(self):
        # Create stations layer
        stations = ogr.GetDriverByName("memory").CreateDataSource("stations")
        stations_layer = create_ogr_layer_from_timeseries(
            self.config.files, self.config.epsg, stations
        )

        # Get mask
        mask = gdal.Open(self.config.mask)

        # Setup integration method
        if self.config.method == "idw":
            funct = idw
            kwargs = {"alpha": self.config.alpha}
        else:
            assert False

        for date in self._dates_to_calculate:
            self.logger.info("Processing date " + date.isoformat())
            h_integrate(
                mask,
                stations_layer,
                date,
                os.path.join(self.config.output_dir, self.config.filename_prefix),
                self._date_fmt,
                funct,
                kwargs,
            )
        self._delete_obsolete_files()


class AppConfig:
    config_file_options = {
        "logfile": {"fallback": ""},
        "loglevel": {"fallback": "warning"},
        "mask": {},
        "epsg": {},
        "output_dir": {},
        "filename_prefix": {},
        "number_of_output_files": {},
        "method": {},
        "alpha": {"fallback": "1"},
        "files": {},
    }

    def __init__(self, configfilename):
        self.configfilename = configfilename

    def read(self):
        try:
            self._parse_config()
        except (OSError, configparser.Error) as e:
            raise click.ClickException(str(e))

    def _parse_config(self):
        self._read_config_file()
        self._get_config_options()
        self._parse_config_options()

    def _read_config_file(self):
        self.config = configparser.ConfigParser(interpolation=None)
        try:
            self._read_config_file_assuming_it_has_section_headers()
        except configparser.MissingSectionHeaderError:
            self._read_config_file_without_sections()

    def _read_config_file_assuming_it_has_section_headers(self):
        with open(self.configfilename) as f:
            self.config.read_file(f)

    def _read_config_file_without_sections(self):
        with open(self.configfilename) as f:
            configuration = "[General]\n" + f.read()
        self.config.read_file(StringIO(configuration))

    def _get_config_options(self):
        self.options = {
            opt: self.config.get("General", opt, **kwargs)
            for opt, kwargs in self.config_file_options.items()
        }
        for key, value in self.options.items():
            setattr(self, key, value)

    def _parse_config_options(self):
        self._parse_log_level()
        self._parse_files()
        self._check_method()
        self._parse_epsg()
        self._parse_number_of_output_files()

    def _parse_log_level(self):
        log_levels = ("ERROR", "WARNING", "INFO", "DEBUG")
        self.loglevel = self.loglevel.upper()
        if self.loglevel not in log_levels:
            raise WrongValueError("loglevel must be one of " + ", ".join(log_levels))

    def _parse_files(self):
        self.files = self.files.split("\n")

    def _check_method(self):
        # Check method
        if self.method != "idw":
            raise WrongValueError('Option "method" can currently only be idw')
        # Check alpha
        try:
            self.alpha = float(self.alpha)
        except ValueError:
            raise WrongValueError('Option "alpha" must be a number')

    def _parse_epsg(self):
        try:
            self.epsg = int(self.epsg)
        except ValueError:
            raise WrongValueError('Option "epsg" must be an integer')
        srs = osr.SpatialReference()
        result = srs.ImportFromEPSG(self.epsg)
        if result:
            raise WrongValueError(
                "An error occurred when trying to use epsg={}".format(self.epsg)
            )

    def _parse_number_of_output_files(self):
        try:
            self.number_of_output_files = int(self.number_of_output_files)
        except ValueError:
            raise WrongValueError('Option "number_of_output_files" must be an integer')


@click.command()
@click.argument("configfile")
@click.version_option(
    version=__version__, message="%(prog)s from pthelma v.%(version)s"
)
def main(configfile):
    """Spatial integration"""

    app = App(configfile)
    app.run()

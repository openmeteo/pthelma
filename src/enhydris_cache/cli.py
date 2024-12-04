import configparser
import datetime as dt
import logging
import os
import traceback

import click

from enhydris_cache import TimeseriesCache
from pthelma._version import __version__


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
        self.logger.info("Starting enhydris-cache, " + dt.datetime.today().isoformat())
        try:
            self._execute()
        except Exception as e:
            self.logger.error(str(e))
            self.logger.debug(traceback.format_exc())
            self.logger.info(
                "enhydris-cache terminated with error, "
                + dt.datetime.today().isoformat()
            )
            raise click.ClickException(str(e))
        else:
            self.logger.info(
                "Finished enhydris-cache, " + dt.datetime.today().isoformat()
            )

    def _setup_logger(self):
        self.logger = logging.getLogger("spatialize")
        self._set_logger_handler()
        self.logger.setLevel(self.config.loglevel.upper())

    def _set_logger_handler(self):
        if getattr(self.config, "logfile", None):
            self.logger.addHandler(logging.FileHandler(self.config.logfile))
        else:
            self.logger.addHandler(logging.StreamHandler())

    def _execute(self):
        os.chdir(self.config.cache_dir)
        self.cache = TimeseriesCache(self.config.timeseries_group)
        self.cache.update()


class AppConfig:
    config_file_general_options = {
        "logfile": {"fallback": ""},
        "loglevel": {"fallback": "warning"},
        "cache_dir": {"fallback": os.getcwd()},
    }
    config_file_timeseries_options = {
        "base_url": {},
        "station_id": {},
        "timeseries_id": {},
        "timeseries_group_id": {},
        "auth_token": {"fallback": None},
        "file": {},
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
        self._parse_general_section()
        self._parse_timeseries_sections()

    def _read_config_file(self):
        self.config = configparser.ConfigParser(interpolation=None)
        with open(self.configfilename) as f:
            self.config.read_file(f)

    def _parse_general_section(self):
        options = {
            opt: self.config.get("General", opt, **kwargs)
            for opt, kwargs in self.config_file_general_options.items()
        }
        for key, value in options.items():
            setattr(self, key, value)
        self._parse_log_level()

    def _parse_log_level(self):
        log_levels = ("ERROR", "WARNING", "INFO", "DEBUG")
        self.loglevel = self.loglevel.upper()
        if self.loglevel not in log_levels:
            raise WrongValueError("loglevel must be one of " + ", ".join(log_levels))

    def _parse_timeseries_sections(self):
        self.timeseries_group = []
        for section in self.config:
            if section in ("General", "DEFAULT"):
                continue
            item = self._read_section(section)
            self.timeseries_group.append(item)

    def _read_section(self, section):
        options = {
            opt: self.config.get(section, opt, **kwargs)
            for opt, kwargs in self.config_file_timeseries_options.items()
        }
        options["name"] = section
        try:
            options["station_id"] = int(options["station_id"])
            options["timeseries_group_id"] = int(options["timeseries_group_id"])
            options["timeseries_id"] = int(options["timeseries_id"])
        except ValueError:
            raise WrongValueError(
                '"{}" or "{}" or "{}" is not a valid integer'.format(
                    options["station_id"],
                    options["timeseries_group_id"],
                    options["timeseries_id"],
                )
            )
        return options


@click.command()
@click.argument("configfile")
@click.version_option(
    version=__version__, message="%(prog)s from pthelma v.%(version)s"
)
def main(configfile):
    """Spatial integration"""

    app = App(configfile)
    app.run()

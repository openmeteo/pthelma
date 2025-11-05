from __future__ import annotations

import configparser
import datetime as dt
import logging
import os
import traceback
from typing import Any, Dict, Sequence

import click

from enhydris_cache import TimeseriesCache, TimeseriesGroup
from pthelma._version import __version__


class WrongValueError(configparser.Error):
    pass


class App:
    def __init__(self, configfilename: str) -> None:
        self.configfilename = configfilename
        self.logger: logging.Logger = logging.getLogger("spatialize")
        self.config: AppConfig | None = None
        self.cache: TimeseriesCache | None = None

    def run(self) -> None:
        self.config = AppConfig(self.configfilename)
        self.config.read()
        self._setup_logger()
        self._execute_with_error_handling()

    def _execute_with_error_handling(self) -> None:
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
            raise click.ClickException(str(e)) from e
        else:
            self.logger.info(
                "Finished enhydris-cache, " + dt.datetime.today().isoformat()
            )

    def _setup_logger(self) -> None:
        if self.config is None:
            raise RuntimeError("Configuration has not been loaded")
        self._set_logger_handler(self.config)
        self.logger.setLevel(self.config.loglevel.upper())

    def _set_logger_handler(self, config: AppConfig) -> None:
        if getattr(config, "logfile", None):
            self.logger.addHandler(logging.FileHandler(config.logfile))
        else:
            self.logger.addHandler(logging.StreamHandler())

    def _execute(self) -> None:
        if self.config is None:
            raise RuntimeError("Configuration has not been loaded")
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

    def __init__(self, configfilename: str) -> None:
        self.configfilename = configfilename
        self.config: configparser.ConfigParser | None = None
        self.logfile: str = ""
        self.loglevel: str = "WARNING"
        self.cache_dir: str = os.getcwd()
        self.timeseries_group: Sequence[TimeseriesGroup] = []

    def read(self) -> None:
        try:
            self._parse_config()
        except (OSError, configparser.Error) as e:
            raise click.ClickException(str(e)) from e

    def _parse_config(self) -> None:
        self._read_config_file()
        self._parse_general_section()
        self._parse_timeseries_sections()

    def _read_config_file(self) -> None:
        config = configparser.ConfigParser(interpolation=None)
        with open(self.configfilename) as f:
            config.read_file(f)
        self.config = config

    def _parse_general_section(self) -> None:
        if self.config is None:
            raise RuntimeError("Configuration file has not been read")
        options = {
            opt: self.config.get("General", opt, **kwargs)  # type: ignore[arg-type]
            for opt, kwargs in self.config_file_general_options.items()
        }
        for key, value in options.items():
            setattr(self, key, value)
        self._parse_log_level()

    def _parse_log_level(self) -> None:
        log_levels = ("ERROR", "WARNING", "INFO", "DEBUG")
        self.loglevel = self.loglevel.upper()
        if self.loglevel not in log_levels:
            raise WrongValueError("loglevel must be one of " + ", ".join(log_levels))

    def _parse_timeseries_sections(self) -> None:
        if self.config is None:
            raise RuntimeError("Configuration file has not been read")
        self.timeseries_group = []
        for section in self.config:
            if section in ("General", "DEFAULT"):
                continue
            item = self._read_section(section)
            self.timeseries_group.append(item)  # type: ignore[arg-type]

    def _read_section(self, section: str) -> Dict[str, Any]:
        if self.config is None:
            raise RuntimeError("Configuration file has not been read")
        options: Dict[str, Any] = {
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
            ) from None
        return options


@click.command()
@click.argument("configfile")
@click.version_option(
    version=__version__, message="%(prog)s from pthelma v.%(version)s"
)
def main(configfile: str) -> None:
    """Spatial integration"""

    app = App(configfile)
    app.run()

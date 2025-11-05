from __future__ import annotations

import configparser
import datetime as dt
import logging
import os
import sys
import traceback
from typing import Optional

import click

from haggregate import RegularizationMode, aggregate
from haggregate.regularize import regularize
from htimeseries import HTimeseries


@click.command()
@click.argument("configfile")
def main(configfile: str) -> None:
    """Create lower-step timeseries from higher-step ones"""

    # Start by setting logger to stdout; later we will switch it according to config
    logger = logging.getLogger("haggregate")
    stdout_handler = logging.StreamHandler()
    logger.addHandler(stdout_handler)

    try:
        config = configparser.ConfigParser()
        with open(configfile) as f:
            config.read_file(f)

        # Read the [General] section
        logfile = config.get("General", "logfile", fallback="")
        loglevel = config.get("General", "loglevel", fallback="warning")
        base_dir = config.get("General", "base_dir", fallback=".")
        target_step = config.get("General", "target_step")
        min_count = config.getint("General", "min_count")
        missing_flag = config.get("General", "missing_flag")
        target_timestamp_offset: Optional[str] = config.get(
            "General", "target_timestamp_offset", fallback=None
        )

        # Remove [General] and make sure there are more sections
        config.pop("General")
        if not len(config.sections()):
            raise configparser.NoSectionError("No time series have been specified")

        # Setup logger
        logger.setLevel(loglevel.upper())
        if logfile:
            logger.removeHandler(stdout_handler)
            logger.addHandler(logging.FileHandler(logfile))

        # Log start of execution
        logger.info("Starting haggregate, " + dt.datetime.today().isoformat())

        # Read each section and do the work for it
        for section_name in config.sections():
            section = config[section_name]
            source_file = section.get("source_file")
            target_file = section.get("target_file")
            assert source_file is not None and target_file is not None
            source_filename = os.path.join(base_dir, source_file)
            target_filename = os.path.join(base_dir, target_file)
            method = section.get("method")
            with open(source_filename, newline="\n") as f:
                ts = HTimeseries(
                    f, format=HTimeseries.FILE, default_tzinfo=dt.timezone.utc
                )
            if method == "mean":
                regularization_mode = RegularizationMode.INSTANTANEOUS
            else:
                regularization_mode = RegularizationMode.INTERVAL
            regts = regularize(ts, new_date_flag="DATEINSERT", mode=regularization_mode)
            assert method is not None
            aggts = aggregate(
                regts,
                target_step,
                method,
                min_count=min_count,
                missing_flag=missing_flag,
                target_timestamp_offset=target_timestamp_offset,
            )
            with open(target_filename, "w") as f:
                aggts.write(f, format=HTimeseries.FILE)

        # Log end of execution
        logger.info("Finished haggregate, " + dt.datetime.today().isoformat())

    except Exception as e:
        logger.error(str(e))
        logger.debug(traceback.format_exc())
        raise click.ClickException(str(e))


if __name__ == "__main__":
    sys.exit(main())

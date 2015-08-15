from argparse import ArgumentParser
from datetime import datetime
import logging
import sys
import traceback

import six
from six import StringIO
from six.moves import configparser
from six.moves.configparser import RawConfigParser, NoOptionError, \
    MissingSectionHeaderError


class InvalidOptionError(configparser.Error):
    pass


class WrongValueError(configparser.Error):
    pass


class CliApp(object):
    name = 'Replace me'
    description = 'Replace me'
    #                            Section     Option            Default
    base_config_file_options = {'General': {'logfile':         '',
                                            'loglevel':        'WARNING',
                                            },
                                }
    config_file_options = {}
    cmdline_arguments = {}

    def read_command_line(self):
        parser = ArgumentParser(description=self.description)
        parser.add_argument('config_file', help='Configuration file')
        parser.add_argument('--traceback', action='store_true',
                            help='Display traceback on error')
        for arg in self.cmdline_arguments:
            parser.add_argument(arg, **(self.cmdline_arguments[arg]))
        self.args = parser.parse_args()

    def setup_logger(self):
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(
            getattr(logging, self.config['General']['loglevel']))
        if self.config['General']['logfile']:
            self.logger.addHandler(
                logging.FileHandler(self.config['General']['logfile']))
        else:
            self.logger.addHandler(logging.StreamHandler())

    def read_configuration(self):
        # Assemble config_file_options
        for section in self.base_config_file_options:
            self.config_file_options[section].update(
                self.base_config_file_options[section])

        # Read config
        cp = RawConfigParser()
        cp.read_file = cp.readfp if six.PY2 else cp.read_file
        try:
            with open(self.args.config_file) as f:
                cp.read_file(f)
        except MissingSectionHeaderError:
            # No section headers? Assume the [General] section is implied.
            with open(self.args.config_file) as f:
                configuration = '[General]\n' + f.read()
            cp.read_file(StringIO(configuration))

        # Convert config to dictionary (for Python 2.7 compatibility)
        self.config = {}
        for section in cp.sections():
            self.config[section] = dict(cp.items(section))

        # Set defaults
        for section in self.config:
            section_options_key = section \
                if section in self.config_file_options else 'other'
            section_options = self.config_file_options[section_options_key]
            if section_options == 'nocheck':
                continue
            for option in section_options:
                value = section_options[option]
                if value is not None:
                    self.config[section].setdefault(option, value)

        # Check
        self.check_configuration()

    def check_configuration(self):
        # Check compulsory options and invalid options
        for section in self.config:
            optionsname = (section if section in self.config_file_options
                           else 'other')
            if self.config_file_options[optionsname] == 'nocheck':
                continue
            section_options = self.config_file_options[optionsname]
            for option in section_options:
                if (section_options[option] is None) and (
                        option not in self.config[section]):
                    raise NoOptionError(option, section)
            for option in self.config[section]:
                if option not in section_options:
                    raise InvalidOptionError(
                        'Invalid option {} in section [{}]'
                        .format(option, section))

        self.check_configuration_log_levels()

    def check_configuration_log_levels(self):
        log_levels = ['ERROR', 'WARNING', 'INFO', 'DEBUG']
        if self.config['General']['loglevel'] not in log_levels:
            raise WrongValueError('loglevel must be one of {}'.format(
                ', '.join(log_levels)))

    def run(self, dry=False):
        self.args = None
        self.logger = None
        try:
            self.read_command_line()
            self.read_configuration()
            self.setup_logger()
            self.logger.info(
                'Starting {}, {}'.format(self.name,
                                         datetime.today().isoformat()))
            if not dry:
                self.execute()
        except Exception as e:
            msg = str(e)
            sys.stderr.write(msg + '\n')
            if self.logger:
                self.logger.error(msg)
                self.logger.debug(traceback.format_exc())
            if self.args and self.args.traceback:
                raise
            sys.exit(1)
        finally:
            if self.logger:
                self.logger.info(
                    'Finished {}, {}'.format(self.name,
                                             datetime.today().isoformat()))

    def execute(self):
        raise NotImplementedError("CliApp is an abstract class")

from copy import copy
import os
import sys

import six

from pthelma.cliapp import CliApp, WrongValueError
from pthelma.timeseries import TimeStep, Timeseries, IntervalType


class AggregateApp(CliApp):
    name = 'aggregate'
    description = 'Aggregate time series'
    #                       Section     Option            Default
    config_file_options = {'General': {'base_dir':        None,
                                       'target_step':     None,
                                       'nominal_offset':  '0,0',
                                       'actual_offset':   '0,0',
                                       'missing_allowed': '0.0',
                                       'missing_flag':    'MISSING',
                                       },
                           'other':   {'source_file':     None,
                                       'target_file':     None,
                                       'interval_type':   None,
                                       },
                           }

    def read_configuration(self):
        super(AggregateApp, self).read_configuration()

        # Make some checks
        self.check_configuration_missing_allowed()
        self.check_configuration_target_step()
        self.check_configuration_offset('nominal_offset')
        self.check_configuration_offset('actual_offset')
        for item in self.config:
            if item == 'General':
                continue
            self.check_configuration_item(item)

        # Save some stuff to easy to access variables
        genconfig = self.config['General']
        self.base_dir = genconfig['base_dir']
        self.missing_allowed = float(genconfig['missing_allowed'])
        minutes, months = [int(x.strip())
                           for x in genconfig['target_step'].split(',')]
        nominal_offset = [int(x.strip())
                          for x in genconfig['nominal_offset'].split(',')]
        actual_offset = [int(x.strip())
                         for x in genconfig['actual_offset'].split(',')]
        self.target_step = TimeStep(length_minutes=minutes,
                                    length_months=months,
                                    nominal_offset=nominal_offset,
                                    actual_offset=actual_offset)
        self.missing_flag = genconfig['missing_flag']

        # Convert time series sections into a list
        self.aggregation_items = []
        for section in self.config:
            if section in self.config_file_options:
                continue
            item = copy(self.config[section])
            item['interval_type'] = IntervalType.__dict__[
                item['interval_type'].upper()]
            self.aggregation_items.append(item)

    def check_configuration_item(self, item):
        interval_type = self.config[item]['interval_type'].upper()
        if interval_type not in IntervalType.__dict__:
            raise WrongValueError('{} is not a valid interval type'.
                                  format(interval_type.lower()))

    def check_configuration_missing_allowed(self):
        missing_allowed = self.config['General']['missing_allowed']
        try:
            ma = float(missing_allowed)
        except ValueError:
            raise WrongValueError('{} is not a number'.format(missing_allowed))
        if ma < 0.0 or ma >= 1.0:
            raise WrongValueError('missing_allowed must be '
                                  'between 0 and 1')

    def check_configuration_target_step(self):
        target_step = self.config['General']['target_step']
        try:
            minutes, months = [int(x.strip()) for x in target_step.split(',')]
            if minutes and months:
                raise ValueError("not both minutes and months can be nonzero")
            if not minutes and not months:
                raise ValueError("one of minutes and months must be nonzero")
        except (IndexError, ValueError):
            raise WrongValueError(
                '"{}" is not an appropriate time step; use "X,Y" where X is '
                'minutes and Y is months; one and only one must be nonzero.'
                .format(target_step))

    def check_configuration_offset(self, offsetname):
        offset = self.config['General'][offsetname]
        try:
            minutes, months = [int(x.strip()) for x in offset.split(',')]
        except (IndexError, ValueError):
            raise WrongValueError(
                '"{}" is not an appropriate offset; use "X,Y" where X is '
                'minutes and Y is months.'.format(offset))

    def execute(self):
        if self.base_dir:
            os.chdir(self.base_dir)
        for item in self.aggregation_items:
            self.logger.info('Processing {}'.format(item['source_file']))
            try:
                self.execute_item(item)
            except Exception as e:
                exc_class, exc, tb = sys.exc_info()
                new_exception = Exception(
                    'A {} occurred while processing {}: {}'.format(
                        exc_class.__name__,
                        os.path.join(self.base_dir, item['source_file']),
                        str(e)))
                if six.PY2:
                    exec('raise new_exception.__class__, new_exception, tb')
                else:
                    raise new_exception.with_traceback(tb)

    def execute_item(self, item):
        source_ts = Timeseries()
        with open(item['source_file']) as f:
            source_ts.read_file(f)
        self.target_step.interval_type = item['interval_type']
        target_ts, missing = source_ts.aggregate(
            self.target_step,
            missing_allowed=self.missing_allowed,
            missing_flag=self.missing_flag)
        with open(item['target_file'], 'w') as f:
            target_ts.write_file(f, version=3)

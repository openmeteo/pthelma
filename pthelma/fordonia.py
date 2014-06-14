from copy import copy
from datetime import timedelta

from pthelma import enhydris_api
from pthelma.cliapp import CliApp, WrongValueError
from pthelma.timeseries import add_months_to_datetime


class FordoniaApp(CliApp):
    name = 'fordonia'
    description = 'Aggregate time series'
                          # Section     Option            Default
    config_file_options = {'General': {'base_url':        None,
                                       'user':            None,
                                       'password':        None,
                                       },
                           'other':   {'source_id':       None,
                                       'target_id':       None,
                                       'missing_allowed': 0.0,
                                       'missing_flag':    'MISSING',
                                       }
                           }

    def read_configuration(self):
        super(FordoniaApp, self).read_configuration()

        # Convert time series sections into a list
        self.aggregation_items = []
        for section in self.config:
            if section in self.config_file_options:
                continue
            item = copy(self.config[section])
            item['source_id'] = int(item['source_id'])
            item['target_id'] = int(item['target_id'])
            item['missing_allowed'] = float(item['missing_allowed'])
            self.aggregation_items.append(item)

        # Save some stuff to easy to access variables
        self.base_url = self.config['General']['base_url']
        self.user = self.config['General']['user']
        self.password = self.config['General']['password']

    def check_configuration(self):
        super(FordoniaApp, self).check_configuration()

        self.check_configuration_aggregation_items()

    def check_configuration_aggregation_items(self):
        for item in self.aggregation_items:
            ma = item['missing_allowed']
            if ma < 0.0 or ma >= 1.0:
                raise WrongValueError('missing_allowed must be '
                                      'between 0 and 1')

    def execute(self):
        self.session_cookies = enhydris_api.login(self.base_url, self.user,
                                                  self.password)
        for item in self.aggregation_items:
            self.execute_item(item)

    def execute_item(self, item):
        # Find the actual end date of the target time series (actual means
        # after dealing with the actual_offset). This is also the actual start
        # date of the source time series (because we need the source time
        # series from that point onwards).
        target_ts = enhydris_api.get_model(
            self.base_url, self.session_cookies, 'Timeseries',
            item['target_id'])
        target_end_date = enhydris_api.get_ts_end_date(
            self.base_url, self.session_cookies, item['target_id'])
        target_actual_end_date = add_months_to_datetime(
            target_end_date, target_ts.actual_offset_months) + timedelta(
            minutes=target_ts.actual_offset_minutes)

        # Given the actual end date of target, aka actual start date of source,
        # deal with the source's actual_offset to determine the source's
        # nominal start date.
        source_ts = enhydris_api.get_model(
            self.base_url, self.session_cookies, 'Timeseries',
            item['source_id'])
        source_start_date = add_months_to_datetime(
            target_actual_end_date, -source_ts.actual_offset_months) + \
            timedelta(minutes=-source_ts.actual_offset_minutes)

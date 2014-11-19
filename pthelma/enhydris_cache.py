import codecs
from copy import copy
from datetime import datetime, timedelta
import os

from six import StringIO

import requests
from requests.exceptions import HTTPError

from pthelma import enhydris_api
from pthelma.cliapp import CliApp, WrongValueError
from pthelma.timeseries import Timeseries


class TimeseriesCache(object):

    def __init__(self, timeseries_group):
        self.timeseries_group = timeseries_group

    def update(self):
        for item in self.timeseries_group:
            self.base_url = item['base_url']
            if self.base_url[-1] != '/':
                self.base_url += '/'
            self.timeseries_id = item['id']
            self.user = item['user']
            self.password = item['password']
            self.filename = item['file']
            self.update_for_one_timeseries()

    def update_for_one_timeseries(self):
        ts1 = self.read_timeseries_from_cache_file()
        end_date = self.get_timeseries_end_date(ts1)
        start_date = end_date + timedelta(minutes=1)
        self.append_newer_timeseries(start_date, ts1)
        with codecs.open(self.filename, 'w', 'utf-8') as f:
            ts1.write_file(f, version=3)

    def read_timeseries_from_cache_file(self):
        result = Timeseries()
        if os.path.exists(self.filename):
            with open(self.filename) as f:
                try:
                    result.read_file(f)
                except ValueError:
                    # File may be corrupted; continue with empty time series
                    result = Timeseries()
        return result

    def get_timeseries_end_date(self, timeseries):
        try:
            end_date = timeseries.bounding_dates()[1]
        except TypeError:
            # Timeseries is totally empty; no start and end date
            end_date = datetime(1, 1, 1, 0, 0)
        return end_date

    def append_newer_timeseries(self, start_date, ts1):
        self.session_cookies = enhydris_api.login(self.base_url, self.user,
                                                  self.password)
        url = self.base_url + 'timeseries/d/{}/download/{}/?version=3'.format(
            self.timeseries_id, start_date.isoformat())
        r = requests.get(url, cookies=self.session_cookies)
        if r.status_code != 200:
            raise HTTPError('Error {} while getting {}'.format(r.status_code,
                                                               url))
        responseio = StringIO(r.text)
        ts2 = Timeseries()
        ts2.read_file(responseio)
        responseio.seek(0)
        ts1.read_meta(responseio)
        ts1.append(ts2)


class EnhydrisCacheApp(CliApp):
    name = 'enhydris_cache'
    description = 'Local filesystem cache of Enhydris data'
    #                       Section     Option      Default
    config_file_options = {'General': {'cache_dir': os.getcwd()
                                       },
                           'other':   {'base_url':  None,
                                       'id':        None,
                                       'user':      '',
                                       'password':  '',
                                       'file':      None,
                                       },
                           }

    def read_configuration(self):
        super(EnhydrisCacheApp, self).read_configuration()

        # Convert all sections but 'General' into a list of time series
        self.timeseries_group = []
        for section in self.config:
            if section == 'General':
                continue
            item = copy(self.config[section])
            item['name'] = section
            try:
                item['id'] = int(item['id'])
            except ValueError:
                raise WrongValueError(
                    '"{}" is not a valid integer'.format(item['id']))
            self.timeseries_group.append(item)

    def execute(self):
        os.chdir(self.config['General']['cache_dir'])
        self.cache = TimeseriesCache(self.timeseries_group)
        self.cache.update()

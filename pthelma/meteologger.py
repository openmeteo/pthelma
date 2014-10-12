#!/usr/bin/python
"""
meteologger - utilities to read files of meteorological loggers

Copyright (C) 2005-2011 National Technical University of Athens
Copyright (C) 2005 Antonios Christofides

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from copy import copy
from datetime import datetime, timedelta
from glob import glob
import math
import os
import re
import struct
import sys
import traceback

from six import StringIO

import iso8601
from pytz import timezone
from simpletail import ropen

from pthelma import enhydris_api
from pthelma.cliapp import CliApp
from pthelma.timeseries import add_months_to_datetime, \
    isoformat_nosecs, Timeseries


class MeteologgerError(Exception):
    pass


class MeteologgerReadError(MeteologgerError):
    pass


class MeteologgerServerError(MeteologgerError):
    pass


class ConfigurationError(MeteologgerError):
    pass


def _next_month(month, year):
    month += 1
    if month > 12:
        month = 1
        year += 1
    return month, year


def _diff_dow(dow1, dow2):
    """
    How many days we need to add to week day dow2 to reach dow1.
    For example, if dow2 is Monday and dow1 is Sunday, the result is 6.
    Monday is 1, Sunday is 7.
    """
    result = dow1 - dow2
    if result < 0:
        result = 7 + result
    return result


def _diff_months(month1, month2):
    result = abs(month2 - month1)
    if result > 6:
        result = 12 - result
    return result


class Datafile(object):
    required_options = ['filename', 'datafile_format', 'datafile_fields']
    optional_options = ['nullstr', 'timezone']

    def __init__(self, base_url, cookies, datafiledict, logger=None):
        self.check_config(datafiledict)
        self.base_url = base_url
        self.cookies = cookies
        self.filename = datafiledict['filename']
        self.datafile_fields = [
            int(x) for x in datafiledict.get('datafile_fields', '').split(',')
            if x != '']
        self.subset_identifiers = datafiledict.get('subset_identifiers', '')
        self.delimiter = datafiledict.get('delimiter', None)
        self.decimal_separator = datafiledict.get('decimal_separator', '')
        self.date_format = datafiledict.get('date_format', '')
        self.nullstr = datafiledict.get('nullstr', '')
        self.nfields_to_ignore = int(datafiledict.get('nfields_to_ignore',
                                     '0'))
        self.timezone = timezone(datafiledict.get('timezone', 'UTC'))
        self.logger = logger
        if not self.logger:
            import logging
            self.logger = logging.getLogger('datafile')
            self.logger.setLevel(logging.WARNING)
            self.logger.addHandler(logging.StreamHandler())

    def check_config(self, datafiledict):
        for option in self.required_options:
            if option not in datafiledict:
                raise ConfigurationError('Option "{}" is required'
                                         .format(option))
        all_options = self.required_options + self.optional_options
        for option in datafiledict:
            if option not in all_options:
                raise ConfigurationError('Unknown option "{}"'.format(option))

    def update_database(self):
        self.logger.info('Processing datafile %s' % (self.filename))
        self.last_timeseries_end_date = None
        self.seq = 0  # sequence number of timeseries
        for self.ts in self.datafile_fields:
            self.seq = self.seq + 1
            if self.ts == 0:
                self.logger.info('Omitting position %d' % (self.seq))
                continue
            self.logger.info('Processing timeseries %d at position %d'
                             % (self.ts, self.seq))
            self._update_timeseries()

    def _get_records_to_append(self, end_date_in_database):
        if (not self.last_timeseries_end_date) or (
                end_date_in_database != self.last_timeseries_end_date):
            self.last_timeseries_end_date = end_date_in_database
            self.logger.info('Reading datafile tail')
            self._get_tail()
            self.logger.info('%d lines in datafile tail' % (len(self.tail)))
            if len(self.tail) > 0:
                self.logger.info('First date in datafile tail: %s' %
                                 (self.tail[0]['date'].isoformat(),))
        ts = Timeseries(self.ts)
        try:
            for line in self.tail:
                v, f = self.extract_value_and_flags(line['line'], self.seq)
                if self.decimal_separator and (self.decimal_separator != '.'):
                    v = v.replace(self.decimal_separator, '.')
                ts[isoformat_nosecs(line['date'])] = (v, f)
        except ValueError as e:
            message = 'parsing error while trying to read values: ' + str(e)
            self.raise_error(line, message)

        return ts

    def _update_timeseries(self):
        end_date_in_database = enhydris_api.get_ts_end_date(
            self.base_url, self.cookies, self.ts)
        self.logger.info('Last date in database: {}'
                         .format(end_date_in_database))
        ts_to_append = self._get_records_to_append(end_date_in_database)
        self.logger.info('Appending %d records' % (len(ts_to_append)))
        if len(ts_to_append):
            self.logger.info('First appended record: %s' %
                             (ts_to_append.items()[0][0].isoformat()))
            self.logger.info('Last appended record:  %s' %
                             (ts_to_append.items()[-1][0].isoformat()))
        self._append_records_to_database(ts_to_append)

    def _append_records_to_database(self, ts_to_append):
        fp = StringIO()
        ts_to_append.write(fp)
        r = enhydris_api.post_tsdata(self.base_url, self.cookies, ts_to_append)
        self.logger.info(
            'Successfully appended {0} records'.format(r))

    def _get_tail(self):
        "Read the part of the datafile after last_timeseries_end_date"
        self.tail = []
        prev_date = ''
        with ropen(self.filename) as xr:
            for line in xr:
                self.logger.debug(line)
                if line.strip() and self.subset_identifiers_match(line):
                    date = self.extract_date(line).replace(second=0)
                    date = self._fix_dst(date)
                    if date == prev_date:
                        w = 'WARNING: Omitting line with repeated date ' + str(
                            date)
                        self.logger.warning(w)
                        continue
                    prev_date = date
                    self.logger.debug('Date: %s' % (date.isoformat()))
                    if date <= self.last_timeseries_end_date:
                        break
                    self.tail.append({'date': date, 'line': line})
        self.tail.reverse()

    def _fix_dst(self, adatetime, now=None):
        """Remove any DST from a date.

           Determine if a date contains DST. If it does, remove the
           extra hour. Returns the fixed date.

           The "now" argument is only used for testing. Normally the method
           assigns the current datetime to it. However, when testing, we
           sometimes want to pretend the time is different.
        """
        result = adatetime
        if self.timezone.zone != 'UTC':
            if not now:
                now = datetime.now(self.timezone)
            now_naive = now.replace(tzinfo=None)
            is_dst = bool(now.dst()) and (
                abs(adatetime - now_naive) < timedelta(hours=24))
            result -= self.timezone.dst(adatetime, is_dst=is_dst)
        return result

    def subset_identifiers_match(self, line):
        "Returns true if subset identifier of line matches specified"
        return True

    def extract_date(self, line):
        raise Exception(
            "Internal error: datafile.extract_date is an abstract function")

    def extract_value_and_flags(self, line, seq):
        raise Exception("Internal error: datafile.extract_value_and_flags "
                        "is an abstract function")

    def raise_error(self, line, msg):
        errmessage = '%s: "%s": %s' % (self.filename, line, msg)
        self.logger.error("Error while parsing, message: %s" % errmessage)
        raise MeteologgerReadError(errmessage)


class Datafile_deltacom(Datafile):
    deltacom_flags = {'#': 'LOGOVERRUN',
                      '$': 'LOGNOISY',
                      '%': 'LOGOUTSIDE',
                      '&': 'LOGRANGE'}

    def extract_date(self, line):
        try:
            return iso8601.parse_date(line.split()[0], default_timezone=None)
        except ValueError:
            self.raise_error(line, 'parse error or invalid date')

    def extract_value_and_flags(self, line, seq):
        flags = ''
        item = line.split()[seq].strip()
        if item[-1] in self.deltacom_flags.keys():
            flags = self.deltacom_flags[item[-1]]
            item = item[:-1]
        if self.nullstr:
            if item == self.nullstr:
                item = float('NaN')
        return (item, flags)


class Datafile_pc208w(Datafile):
    required_options = Datafile.required_options + [
        'subset_identifiers']

    def extract_date(self, line):
        try:
            items = line.split(',')
            year = int(items[2])
            yday = int(items[3])
            hour = int(items[4]) / 100
            minute = int(items[4]) % 100
            if hour == 24:
                hour = 0
                yday = yday + 1
            return datetime(year, 1, 1, hour, minute) + timedelta(yday - 1)
        except StandardError:
            self.raise_error(line, 'parse error or invalid date')

    def extract_value_and_flags(self, line, seq):
        try:
            item = line.split(',')[seq + 4].strip()
        except IndexError:
            raise ValueError()
        if self.nullstr:
            if item == self.nullstr:
                item = float('NaN')
        return (item, '')

    def subset_identifiers_match(self, line):
        si = line.split(',')[0].strip()
        return si == self.subset_identifiers


class Datafile_CR1000(Datafile):
    required_options = Datafile.required_options + [
        'subset_identifiers']

    def extract_date(self, line):
        try:
            datestr = line.split(',')[0].strip('"')
            return iso8601.parse_date(datestr[:16], default_timezone=None)
        except StandardError:
            self.raise_error(line, 'parse error or invalid date')

    def extract_value_and_flags(self, line, seq):
        return (line.split(',')[seq + 3].strip(), '')

    def subset_identifiers_match(self, line):
        si = line.split(',')[2].strip()
        return si == self.subset_identifiers


class Datafile_simple(Datafile):
    optional_options = Datafile.optional_options + [
        'nfields_to_ignore', 'delimiter', 'date_format']

    def __init__(self, base_url, cookies, datafiledict, logger=None):
        super(Datafile_simple, self).__init__(base_url, cookies, datafiledict,
                                              logger)
        self.__separate_time = False

    def extract_date(self, line):
        try:
            items = line.split(self.delimiter)
            datestr = items[self.nfields_to_ignore].strip('"')
            self.__separate_time = False
            if len(datestr) <= 10:
                datestr += ' ' + items[self.nfields_to_ignore + 1].strip('"')
                self.__separate_time = True
            if self.date_format:
                result = datetime.strptime(datestr, self.date_format).replace(
                    second=0)
            else:
                result = iso8601.parse_date(datestr[:16],
                                            default_timezone=None)
            return result
        except ValueError as e:
            self.raise_error(line.strip(), "invalid date '{0}': {1}".format(
                datestr, str(e)))

    def extract_value_and_flags(self, line, seq):
        index = self.nfields_to_ignore + seq + (
            1 if self.__separate_time else 0)
        value = line.split(self.delimiter)[index].strip().strip('"').strip()
        if self.nullstr and value == self.nullstr:
            value = float('NaN')
        return (value, '')


class Datafile_lastem(Datafile):
    required_options = Datafile.required_options + [
        'subset_identifiers']
    optional_options = Datafile.optional_options + [
        'delimiter', 'decimal_separator', 'date_format']

    def extract_date(self, line):
        try:
            date = line.split(self.delimiter)[3]
            return datetime.strptime(date, self.date_format)
        except StandardError:
            self.raise_error(line, 'parse error or invalid date')

    def extract_value_and_flags(self, line, seq):
        value = line.split(self.delimiter)[seq + 3]
        if self.nullstr:
            if value == self.nullstr:
                value = float('NaN')
        if not math.isnan(value):
            value = value.replace(self.decimal_separator, '.')
        return (value, '')

    def subset_identifiers_match(self, line):
        si = [x.strip() for x in line.split(self.delimiter)[0:3]]
        si1 = [x.strip() for x in self.subset_identifiers.split(',')]
        return si == si1


class Datafile_wdat5(Datafile):
    wdat_record_format = [
        '<b dataType',
        '<b archiveInterval',
        '<b iconFlags',
        '<b moreFlags',
        '<h packedTime',
        '<h outsideTemp',
        '<h hiOutsideTemp',
        '<h lowOutsideTemp',
        '<h insideTemp',
        '<h barometer',
        '<h outsideHum',
        '<h insideHum',
        '<H rain',
        '<h hiRainRate',
        '<h windSpeed',
        '<h hiWindSpeed',
        '<b windDirection',
        '<b hiWindDirection',
        '<h numWindSamples',
        '<h solarRad',
        '<h hiSolarRad',
        '<B UV',
        '<B hiUV',
        '<b leafTemp1', '<b leafTemp2',
        '<b leafTemp3', '<b leafTemp4',
        '<h extraRad',
        '<h newSensors1', '<h newSensors2', '<h newSensors3',
        '<h newSensors4', '<h newSensors5', '<h newSensors6',
        '<b forecast',
        '<B ET',
        '<b soilTemp1', '<b soilTemp2', '<b soilTemp3',
        '<b soilTemp4', '<b soilTemp5', '<b soilTemp6',
        '<b soilMoisture1', '<b soilMoisture2', '<b soilMoisture3',
        '<b soilMoisture4', '<b soilMoisture5', '<b soilMoisture6',
        '<b leafWetness1', '<b leafWetness2',
        '<b leafWetness3', '<b leafWetness4',
        '<b extraTemp1', '<b extraTemp2', '<b extraTemp3',
        '<b extraTemp4', '<b extraTemp5', '<b extraTemp6',
        '<b extraTemp7',
        '<b extraHum1', '<b extraHum2', '<b extraHum3',
        '<b extraHum4', '<b extraHum5', '<b extraHum6',
        '<b extraHum7',
    ]
    required_options = [x for x in Datafile.required_options
                        if x != 'datafile_fields']
    variables_labels = [x.split()[1].lower() for x in wdat_record_format[5:]]
    optional_options = variables_labels + ['timezone']

    def __init__(self, base_url, cookies, datafiledict, logger=None):
        super(Datafile_wdat5, self).__init__(base_url, cookies, datafiledict,
                                             logger)

        self.variables = {}
        for label in self.variables_labels:
            self.variables[label] = datafiledict.get(label, None)

        unit_parameters = {
            'temperature_unit': ('C', 'F'),
            'rain_unit': ('mm', 'inch'),
            'wind_speed_unit': ('m/s', 'mph'),
            'pressure_unit': ('hPa', 'inch Hg'),
            'matric_potential_unit': ('centibar', 'cm'),
        }
        for p in unit_parameters:
            self.__dict__[p] = datafiledict.get(p, unit_parameters[p][0])
            if self.__dict__[p] not in unit_parameters[p]:
                raise ConfigurationError("{0} must be one of {1}".format(
                    p, ', '.join(unit_parameters[p])))

    def update_database(self):
        self.logger.info('Processing data directory %s' % (self.filename))
        self.last_timeseries_end_date = None
        for self.seq, label in enumerate(self.variables_labels, start=1):
            self.ts = self.variables.get(label, None)
            if not self.ts:
                self.logger.debug('Omitting {}'.format(label))
                continue
            self.logger.info('Processing timeseries {} as {}'.format(self.ts,
                                                                     label))
            self._update_timeseries()

    def _get_tail(self):
        "Read the part of the data after last_timeseries_end_date"
        self.tail = []
        date = self.last_timeseries_end_date
        saveddir = os.getcwd()
        try:
            os.chdir(self.filename)

            # We assume that the first possible file we need to read is the
            # previous than what it seems initially, because of the possibility
            # of a DST offset interfering (I think that actually a negative DST
            # offset would be needed for this to be a problem - but let's be
            # safe and not sorry) (note that if the date is 0001-01-01 it
            # means that the time series in the database is empty and we'll
            # upload it in its entirety anyway, so no need to do the trick
            # [which would fail because dates can't be less than that]).
            a = add_months_to_datetime(date, -1) if date.year > 1 else date
            first_file = '{0.year:04}-{0.month:02}.wlk'.format(a)

            filename_regexp = re.compile(r'\d{4}-\d{2}.wlk$')
            data_files = [x for x in glob('*.wlk')
                          if filename_regexp.match(x) and x >= first_file]
            data_files.sort()
            for current_file in data_files:
                self.tail.extend(self._get_tail_part(date, current_file))
        finally:
            os.chdir(saveddir)

    def _get_tail_part(self, last_date, filename):
        """
        Read a single wdat5 file.

        Reads the single wdat5 file "filename" for records with
        date>last_date, and returns a list of records in space-delimited
        format; iso datetime first, values after.
        """
        year, month = [int(x) for x
                       in os.path.split(filename)[1].split('.')[0].split('-')]
        result = []
        with open(filename, 'rb') as f:
            header = f.read(212)
            if header[:6] != b'WDAT5.':
                raise MeteologgerReadError('File {0} does not appear to be '
                                           'a WDAT 5.x file'.format(filename))
            for day in range(1, 32):
                day_index = header[20 + (day * 6):20 + (day * 6) + 6]
                records_in_day = struct.unpack('<h', day_index[:2])[0]
                start_pos = struct.unpack('<l', day_index[2:])[0]
                for r in range(records_in_day):
                    f.seek(212 + ((start_pos + r) * 88))
                    record = f.read(88)
                    if record[0] != b'\x01'[0]:
                        continue
                    decoded_record = self._decode_wdat_record(record)
                    date = datetime(year=year, month=month, day=day) + \
                        timedelta(minutes=decoded_record['packedTime'])
                    date = self._fix_dst(date)
                    if date <= last_date:
                        continue
                    result.append({'date': date,
                                   'line': self._convert_wdat_record(
                                       date, decoded_record)})
        return result

    def _decode_wdat_record(self, record):
        "Decode bytes into a dictionary"
        result = {}
        offset = 0
        for item in self.wdat_record_format:
            fmt, name = item.split()
            result[name] = struct.unpack_from(fmt, record, offset)[0]
            offset += struct.calcsize(fmt)
        return result

    def _convert_wdat_record(self, date, decoded_record):
        "Return a space-delimited string based on the decoded record"
        r = copy(decoded_record)

        # Temperature
        for x in ['outsideTemp', 'hiOutsideTemp', 'lowOutsideTemp',
                  'insideTemp']:
            r[x] = (r[x] / 10.0 if self.temperature_unit == 'F' else
                    ((r[x] / 10.0) - 32) * 5 / 9.0)

        # Pressure
        r['barometer'] = (r['barometer'] / 1000.0
                          if self.pressure_unit == 'inch Hg'
                          else r['barometer'] / 1000.0 * 25.4 * 1.33322387415)

        # Humidity
        for x in ['outsideHum', 'insideHum']:
            r[x] = r[x] / 10.0

        # Rain
        rain_collector_type = r['rain'] & 0xF000
        rain_clicks = r['rain'] & 0x0FFF
        depth_per_click = {
            0x0000: 0.1 * 25.4,
            0x1000: 0.01 * 25.4,
            0x2000: 0.2,
            0x3000: 1.0,
            0x6000: 0.1,
        }[rain_collector_type]
        depth = depth_per_click * rain_clicks
        r['rain'] = depth / 25.4 if self.rain_unit == 'inch' else depth
        rate = r['hiRainRate'] * depth_per_click
        r['hiRainRate'] = rate / 25.4 if self.rain_unit == 'inch' else rate

        # Wind speed
        def convert_wind_speed(x):
            return (x / 10.0 if self.wind_speed_unit == 'mph'
                    else x / 10.0 * 1609.344 / 3600)

        r['windSpeed'] = convert_wind_speed(r['windSpeed'])
        r['hiWindSpeed'] = convert_wind_speed(r['hiWindSpeed'])

        # Wind direction
        for x in ['windDirection', 'hiWindDirection']:
            r[x] = r[x] / 16.0 * 360 if r[x] >= 0 else 'NaN'

        # UV index
        r['UV'] = r['UV'] / 10.0
        r['hiUV'] = r['hiUV'] / 10.0

        # Evapotranspiration
        r['ET'] = (r['ET'] / 1000.0 if self.rain_unit == 'inch'
                   else r['ET'] / 1000.0 * 25.4)

        # Matric potential
        for i in range(1, 7):
            varname = 'soilMoisture' + str(i)
            r[varname] = (r[varname]
                          if self.matric_potential_unit == 'centibar'
                          else r[varname] / 9.80638)

        # extraTemp etc.
        for x in ['extraTemp1', 'extraTemp2', 'extraTemp3', 'extraTemp4',
                  'extraTemp5', 'extraTemp6', 'extraTemp7', 'soilTemp1',
                  'soilTemp2', 'soilTemp3', 'soilTemp4', 'soilTemp5',
                  'soilTemp6', 'leafTemp1', 'leafTemp2', 'leafTemp3',
                  'leafTemp4']:
            r[x] = (r[x] - 90 if self.temperature_unit == 'F' else
                    ((r[x] - 90) - 32) * 5 / 9.0)

        result = "{r[outsideTemp]} {r[hiOutsideTemp]} " \
                 "{r[lowOutsideTemp]} {r[insideTemp]} {r[barometer]} " \
                 "{r[outsideHum]} {r[insideHum]} {r[rain]} {r[hiRainRate]} " \
                 "{r[windSpeed]} {r[hiWindSpeed]} " \
                 "{r[windDirection]} {r[hiWindDirection]} " \
                 "{r[numWindSamples]} {r[solarRad]} {r[hiSolarRad]} {r[UV]} " \
                 "{r[hiUV]} " \
                 "{r[leafTemp1]} {r[leafTemp2]} " \
                 "{r[leafTemp3]} {r[leafTemp4]} " \
                 "{r[extraRad]} " \
                 "{r[newSensors1]} {r[newSensors2]} {r[newSensors3]} " \
                 "{r[newSensors4]} {r[newSensors5]} {r[newSensors6]} " \
                 "{r[forecast]} {r[ET]} " \
                 "{r[soilTemp1]} {r[soilTemp2]} {r[soilTemp3]} " \
                 "{r[soilTemp4]} {r[soilTemp5]} {r[soilTemp6]} " \
                 "{r[soilMoisture1]} {r[soilMoisture2]} {r[soilMoisture3]} " \
                 "{r[soilMoisture4]} {r[soilMoisture5]} {r[soilMoisture6]} " \
                 "{r[leafWetness1]} {r[leafWetness2]} " \
                 "{r[leafWetness3]} {r[leafWetness4]} " \
                 "{r[extraTemp1]} {r[extraTemp2]} {r[extraTemp3]} " \
                 "{r[extraTemp4]} {r[extraTemp5]} {r[extraTemp6]} " \
                 "{r[extraTemp7]} " \
                 "{r[extraHum1]} {r[extraHum2]} {r[extraHum3]} " \
                 "{r[extraHum4]} {r[extraHum5]} {r[extraHum6]} " \
                 "{r[extraHum7]} ".format(r=r)
        return result

    def extract_value_and_flags(self, line, seq):
        result = line.split()[seq - 1].strip()
        return (result, '')


class Datafile_odbc(Datafile_simple):
    required_options = Datafile.required_options + [
        'table', 'date_sql', 'data_columns']
    optional_options = Datafile.optional_options + ['date_format',
                                                    'decimal_separator']

    def __init__(self, base_url, cookies, datafiledict, logger=None):
        super(Datafile_odbc, self).__init__(base_url, cookies,
                                            datafiledict, logger)
        self.table = datafiledict.get('table', '')
        self.date_sql = datafiledict.get('date_sql', '')
        self.data_columns = datafiledict.get('data_columns', '').split(',')
        self.delimiter = ';'

    def _get_tail(self):
        "Read the part of the datafile after last_timeseries_end_date"
        try:
            import pyodbc
        except ImportError:
            self.logger.error('Install pyodbc to use odbc format')
            raise
        sql = """SELECT {} + ';' + {} FROM "{}" ORDER BY -id""".format(
            self.date_sql,
            " + ';' + ".join(['"{}"'.format(x) for x in self.data_columns]),
            self.table)
        self.tail = []
        connection = pyodbc.connect(self.filename)
        cursor = connection.cursor()
        cursor.execute(sql)
        for row in cursor:  # Iterable cursor is a pyodbc feature
            line = row[0]  # Our SQL returns a single string
            self.logger.debug(line)
            date = self.extract_date(line).replace(second=0)
            date = self._fix_dst(date)
            self.logger.debug('Date: %s' % (date.isoformat()))
            if date <= self.last_timeseries_end_date:
                break
            self.tail.append({'date': date, 'line': line})
        self.tail.reverse()


class LoggertodbApp(CliApp):
    name = 'loggertodb'
    description = 'Insert meteorological logger data to Enhydris'
    config_file_options = {'General': {'base_url': None,
                                       'user':     None,
                                       'password': None,
                                       },
                           'other':   'nocheck',
                           }

    def read_configuration(self):
        super(LoggertodbApp, self).read_configuration()
        if not self.config['General']['base_url'].endswith('/'):
            self.config['General']['base_url'] += '/'

    def execute(self):
        cookies = enhydris_api.login(self.config['General']['base_url'],
                                     self.config['General']['user'],
                                     self.config['General']['password'])
        for section in self.config:
            if section == 'General':
                continue
            datafileclass = eval('Datafile_{}'.format(
                self.config[section]['datafile_format']))
            adatafile = datafileclass(self.config['General']['base_url'],
                                      cookies,
                                      self.config[section],
                                      self.logger)
            try:
                adatafile.update_database()
            except MeteologgerError as e:
                msg = 'Error while processing item {0}: {1}'.format(section,
                                                                    str(e))
                sys.stderr.write(msg + '\n')
                self.logger.error(msg)
                self.logger.debug(traceback.format_exc())

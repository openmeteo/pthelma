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
import struct
from urllib import urlencode
from urllib2 import Request
from StringIO import StringIO

from pytz import timezone

from xreverse import xreverse
from timeseries import Timeseries, datetime_from_iso, isoformat_nosecs


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

    def __init__(self, base_url, opener, datafiledict, logger=None):
        self.base_url = base_url
        self.opener = opener
        self.filename = datafiledict['filename']
        self.datafile_fields = [int(x) for x in datafiledict['datafile_fields']
                                .split(',')]
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

    def update_database(self):
        self.logger.info('Processing datafile %s' % (self.filename))
        self.last_timeseries_end_date = None
        self.fileobject = open(self.filename, 'rb')
        try:
            self.seq = 0  # sequence number of timeseries
            for self.ts in self.datafile_fields:
                self.seq = self.seq + 1
                if self.ts == 0:
                    self.logger.info('Omitting position %d' % (self.seq))
                    continue
                self.logger.info('Processing timeseries %d at position %d'
                                 % (self.ts, self.seq))
                self._update_timeseries()
        finally:
            self.fileobject.close()

    def _get_end_date_in_database(self):
        """Return end date of self.ts in database, or 1/1/1 if timeseries is
           empty
        """
        t = Timeseries()
        t.read(self.opener.open('%stimeseries/d/%d/bottom/' %
                                (self.base_url, self.ts)))
        bounding_dates = t.bounding_dates()
        end_date = bounding_dates[1] if bounding_dates else None
        self.logger.info('Last date in database: %s' % (str(end_date)))
        if not end_date:
            end_date = datetime(1, 1, 1)
        return end_date

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
                ts[isoformat_nosecs(line['date'])] = \
                    self.extract_value_and_flags(line['line'], self.seq)
        except ValueError as e:
            message = 'parsing error while trying to read values: ' + str(e)
            self.raise_error(line, message)

        return ts

    def _update_timeseries(self):
        end_date_in_database = self._get_end_date_in_database()
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
        timeseries_records = fp.getvalue()
        fp = self.opener.open(Request(
            '{0}api/tsdata/{1}/'.format(self.base_url, ts_to_append.id),
            data=urlencode({'timeseries_records': timeseries_records}),
            headers={'Content-type': 'application/x-www-form-urlencoded'}))
        response_text = fp.read()
        if not response_text.isdigit():
            raise MeteologgerServerError(response_text)
        self.logger.info(
            'Successfully appended {0} records'.format(response_text))

    def _get_tail(self):
        "Read the part of the datafile after last_timeseries_end_date"
        self.tail = []
        xr = xreverse(self.fileobject, 2048)
        prev_date = ''
        while True:
            try:
                line = xr.next()
            except StopIteration:
                break
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

    def _fix_dst(self, adatetime):
        """Remove any DST from a date.
           Determine if a date contains DST. If it does, remove the
           extra hour. Returns the fixed date."""
        result = adatetime
        if self.timezone.zone != 'UTC':
            is_dst = bool(datetime.now(self.timezone).dst())
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
            return datetime_from_iso(line)
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

    def extract_date(self, line):
        try:
            datestr = line.split(',')[0].strip('"')
            return datetime_from_iso(datestr[:16])
        except StandardError:
            self.raise_error(line, 'parse error or invalid date')

    def extract_value_and_flags(self, line, seq):
        return (line.split(',')[seq + 3].strip(), '')

    def subset_identifiers_match(self, line):
        si = line.split(',')[2].strip()
        return si == self.subset_identifiers


class Datafile_simple(Datafile):

    def __init__(self, base_url, opener, datafiledict, logger=None):
        super(Datafile_simple, self).__init__(base_url, opener, datafiledict,
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
                result = datetime_from_iso(datestr[:16])
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
        '<h hisolarRad',
        '<b UV',
        '<b hiUV',
        '<b leafTemp1', '<b leafTemp2',
        '<b leafTemp3', '<b leafTemp4',
        '<h extraRad',
        '<h newSensors1', '<h newSensors2', '<h newSensors3',
        '<h newSensors4', '<h newSensors5', '<h newSensors6',
        '<b forecast',
        '<b ET',
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

    def __init__(self, base_url, opener, datafiledict, logger=None):
        super(Datafile_wdat5, self).__init__(base_url, opener, datafiledict,
                                             logger)
        unit_parameters = {
            'temperature_unit': ('C', 'F'),
            'rain_unit': ('mm', 'inch'),
            'wind_speed_unit': ('m/s', 'mph'),
            'pressure_unit': ('hPa', 'inch Hg')
            'matric_potential_unit': ('centibar', 'cm')
        }
        for p in unit_parameters:
            self.__dict__[p] = datafiledict.get(p, unit_parameters[p][0])
            if self.__dict__[p] not in unit_parameters[p]:
                raise ConfigurationError("{0} must be one of {1}".format(
                    p, ', '.join(unit_parameters[p])))

    def update_database(self):
        self.logger.info('Processing data directory %s' % (self.filename))
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

    def _get_tail(self):
        "Read the part of the data after last_timeseries_end_date"
        self.tail = []
        date = self.last_timeseries_end_date
        first_file = os.path.join(self.filename,
                                  '{0.year}-{0.month:02}.wlk'.format(date))
        data_files = [x for x in glob(os.path.join(self.filename), '*.wlk')
                      if x >= first_file]
        data_files.sort()
        for current_file in data_files:
            self.tail.extend(self._get_tail_part(date, current_file))

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
            if header[:7] != 'WDAT5.':
                raise MeteologgerReadError('File {0} does not appear to be '
                                           'a WDAT 5.x file'.format(filename))
            for day in range(1, 31):
                day_index = header[20 + (day * 6):20 + (day * 6) + 6]
                records_in_day = struct.unpack('<h', day_index[:2])
                start_pos = struct.unpack('<l', day_index[2:])
                for r in range(records_in_day):
                    f.fseek(212 + ((start_pos + r) * 88))
                    record = f.read(88)
                    if ord(record[0]) != 1:
                        continue
                    decoded_record = self._decode_wdat_record(record)
                    date = datetime(year=year, month=month, day=day) + \
                        timedelta(minutes=decoded_record['packedTime'])
                    if date <= last_date:
                        continue
                    result.append(self._convert_wdat_record(date,
                                                            decoded_record))
        return result

    def _decode_wdat_record(self, record):
        "Decode bytes into a dictionary"
        result = {}
        offset = 0
        for item in self.wdat_record_format:
            fmt, name = item.split()
            result[name] = struct.unpack_from(fmt, record, offset)
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
            0x2000: 0.3,
            0x3000: 1.0,
            0x6000: 0.1,
        }[rain_collector_type]
        depth = depth_per_click * rain_clicks
        r['rain'] = depth / 25.4 if self.rain_unit == 'inch' else depth
        rate = r['hiRainRate'] * depth_per_click
        r['hiRainRate'] = rate / 25.4 if self.rain_unit == 'inch' else rate

        # Wind speed
        r['hiWindSpeed'] = (r['hiWindSpeed'] if self.wind_speed_unit == 'mph'
                            else r['hiWindSpeed'] * 1609.344 / 3600)

        # Wind direction
        for x in ['windDirection', 'hiWindDirection']:
            r[x] = r[x] / 16.0 * 360

        # UV index
        r['UV'] = r['UV'] / 10.0
        r['hiUV'] = r['hiUV'] / 10.0

        # Evapotranspiration
        r['ET'] = (r['ET'] / 1000.0 if self.rain_unit == 'inch'
                   else r['ET'] / 1000.0 * 25.4)

        # Matric potential
        r['soilMoisture'] = (r['soilMoisture']
                             if self.matric_potential_unit == 'centibar'
                             else r['soilMoisture'] / 9.80638)

        # extraTemp etc.
        for x in ['extraTemp1', 'extraTemp2', 'extraTemp3', 'extraTemp4',
                  'extraTemp5', 'extraTemp6', 'extraTemp7', 'soilTemp1',
                  'soilTemp2', 'soilTemp3', 'soilTemp4', 'soilTemp5',
                  'soilTemp6', 'leafTemp1', 'leafTemp2', 'leafTemp3',
                  'leafTemp4']:
            r[x] = (r[x] - 90 if self.temperature_unit == 'F' else
                    ((r[x] - 90) - 32) * 5 / 9.0)

        result = "{date} {r.outsideTemp} {r.hiOutsideTemp} " \
                 "{r.lowOutsideTemp} {r.insideTemp} {r.barometer} " \
                 "{r.outsideHum} {r.insideHum} {r.rain} {r.hiRainRate} " \
                 "{r.hiWindSpeed} {r.windDirection} {r.hiWindDirection} " \
                 "{r.numWindSamples} {r.solarRad} {r.hiSolarRad} {r.UV} " \
                 "{r.hiUV} " \
                 "{r.leafTemp1} {r.leafTemp2} {r.leafTemp3} {r.leafTemp4} " \
                 "{r.extraRad} {r.forecast} {r.ET} " \
                 "{r.soilTemp1} {r.soilTemp2} {r.soilTemp3} " \
                 "{r.soilTemp4} {r.soilTemp5} {r.soilTemp6} " \
                 "{r.soilMoisture1} {r.soilMoisture2} {r.soilMoisture3} " \
                 "{r.soilMoisture4} {r.soilMoisture5} {r.soilMoisture6} " \
                 "{r.leafWetness1} {r.leafWetness2} " \
                 "{r.leafWetness3} {r.leafWetness4} " \
                 "{r.extraTemp1} {r.extraTemp2} {r.extraTemp3} " \
                 "{r.extraTemp4} {r.extraTemp5} {r.extraTemp6} " \
                 "{r.extraTemp7} " \
                 "{r.extraHum1} {r.extraHum2} {r.extraHum3} " \
                 "{r.extraHum4} {r.extraHum5} {r.extraHum6} " \
                 "{r.extraHum7} ".format(date=date, r=r)
        return result

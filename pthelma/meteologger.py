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

from datetime import datetime, timedelta, time
import math
from urllib import urlencode
from urllib2 import Request
from StringIO import StringIO

from xreverse import xreverse
from timeseries import Timeseries, datetime_from_iso, isoformat_nosecs


class MeteologgerError(StandardError): pass
class MeteologgerReadError(MeteologgerError): pass
class MeteologgerServerError(MeteologgerError): pass
class DSTSpecificationParseError(MeteologgerError): pass


def __parse_dst_spec(dst_spec):
    """
    Parse a dst specification and return it as a dictionary.  The returned
    dictionary contains items "time", "month", and either "dow",  and "nth",
    or "dom".  "month" is an integer 1 to 12.  "dow" can be 1 to 7 for
    Monday to Sunday; "nth" can be 1 to 4 for first to fourth, or -1 for
    last; "dom" is the day of month.  "time" is a datetime.time object.
    """
    nth_values = { "first": 1, "second": 2, "third": 3, "fourth": 4,
                   "last": -1 }
    month_values = { "january": 1, "february": 2, "march": 3, "april": 4,
                     "may": 5, "june": 6, "july": 7, "august": 8,
                     "september": 9, "october": 10, "november": 11,
                     "december": 12 }
    dow_values = { "monday": 1, "tuesday": 2, "wednesday": 3, "thursday": 4,
                   "friday": 5, "saturday": 6, "sunday": 7 }
    result = { }
    items = dst_spec.split()
    try:
        hour, minute = [int(x) for x in items[-1].split(':')]
        result["time"] = time(hour, minute)
        if len(items) == 2:
            month, dom = [int(x) for x in items[0].split('-')]
            result["month"] = month
            result["dom"] = dom
        elif len(items) == 4:
            result["nth"] = nth_values[items[0].lower()]
            result["month"] = month_values[items[1].lower()]
            result["dow"] = dow_values[items[2].lower()]
        return result
    except (ValueError, IndexError, KeyError):
        raise DSTSpecificationParseError("Cannot parse " + dst_spec)


class Datafile(object):

    def __init__(self, base_url, opener, datafiledict, logger=None):
        self.base_url = base_url
        self.opener = opener
        self.filename = datafiledict['filename']
        self.datafile_fields = [int(x)
                            for x in datafiledict['datafile_fields'].split(',')]
        self.subset_identifiers = datafiledict.get('subset_identifiers', '')
        self.delimiter = datafiledict.get('delimiter', None)
        self.decimal_separator = datafiledict.get('decimal_separator', '')
        self.date_format = datafiledict.get('date_format', '')
        self.nullstr = datafiledict.get('nullstr', '')
        self.nfields_to_ignore = int(datafiledict.get('nfields_to_ignore', '0'))
        self.dst_starts = __parse_dst_spec(datafiledict.get('dst_starts', ''))
        self.dst_ends = __parse_dst_spec(datafiledict.get('dst_ends', ''))
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
            self.seq = 0 # sequence number of timeseries
            for self.ts in self.datafile_fields:
                self.seq = self.seq+1
                if self.ts==0:
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
        if not end_date: end_date = datetime(1, 1, 1)
        return end_date

    def _get_records_to_append(self, end_date_in_database):
        if (not self.last_timeseries_end_date) or (
                          end_date_in_database!=self.last_timeseries_end_date):
            self.last_timeseries_end_date = end_date_in_database
            self.logger.info('Reading datafile tail')
            self._get_tail()
            self.logger.info('%d lines in datafile tail' % (len(self.tail)))
            if len(self.tail)>0:
                self.logger.info('First date in datafile tail: %s' %
                (self.tail[0]['date'].isoformat(),))
        ts = Timeseries(self.ts)
        try:
            for line in self.tail:
                ts[isoformat_nosecs(line['date'])] = \
                    self.extract_value_and_flags(line['line'], self.seq)
        except ValueError as e:
            self.raise_error(line,
                        'parsing error while trying to read values: ' + str(e))
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
                data=urlencode({ 'timeseries_records': timeseries_records }),
                headers={ 'Content-type': 'application/x-www-form-urlencoded' }
                ))
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
            if not line.strip(): continue # skip empty lines
            if not self.subset_identifiers_match(line): continue
            date = self.extract_date(line).replace(second=0)
            date = self._fix_dst(date)
            if date == prev_date:
                w = 'WARNING: Omitting line with repeated date ' + date
                self.logger.warning(w)
                continue
            prev_date = date
            self.logger.debug('Date: %s' % (date.isoformat()))
            if date <= self.last_timeseries_end_date:
                break;
            self.tail.append({ 'date': date, 'line': line })
        self.tail.reverse()

    def _fix_dst(self, date):
        """Remove any DST from a date.
           Determine if a date contains DST. If it does, remove the
           extra hour. Returns the fixed date."""
        if not self.dst_starts:
            return date
        nearest_dst_switch, to_dst = self._nearest_dst_switch(date)

    def _nearest_dst_switch(self, date):
        """
        Determine the dst switching date closest to specified date.
        Returns a tuple, the first item of which is the dst switch
        date and time (without DST), and the second item is True if
        this is a switch to dst and False if it is a switch from DST.
        For example, if dst_start is "last Sunday March 03:00", and
        the specified date is 2013-05-23, this method will return
        (2013-03-31 03:00, True).  Note that it doesn't try to be too
        accurate; if the given date falls an equal number of months
        between switches, it might return either switch.
        """
        pass

    def subset_identifiers_match(self, line):
        "Returns true if subset identifier of line matches specified"
        return True

    def extract_date(self, line):
        raise Exception(
                "Internal error: datafile.extract_date is an abstract function")

    def extract_value_and_flags(self, line, seq):
        raise Exception("Internal error: datafile.extract_value_and_flags " +
                "is an abstract function")

    def raise_error(self, line, msg):
        errmessage = '%s: "%s": %s' % (self.filename, line, msg)
        self.logger.error("Error while parsing, message: %s" % errmessage)
        raise MeteologgerReadError(errmessage)


class Datafile_deltacom(Datafile):
    deltacom_flags = { '#': 'LOGOVERRUN',
                       '$': 'LOGNOISY',
                       '%': 'LOGOUTSIDE',
                       '&': 'LOGRANGE' }

    def extract_date(self, line):
        try: return datetime_from_iso(line)
        except ValueError: self.raise_error(line, 'parse error or invalid date')

    def extract_value_and_flags(self, line, seq):
        flags = ''
        item = line.split()[seq].strip()
        if item[-1] in self.deltacom_flags.keys():
            flags = self.deltacom_flags[item[-1]]
            item = item[:-1]
        if self.nullstr:
            if item==self.nullstr:
                item = float('NaN')
        return (item, flags)


class Datafile_pc208w(Datafile):

    def extract_date(self, line):
        try:
            items = line.split(',')
            year = int(items[2])
            yday = int(items[3])
            hour = int(items[4])/100
            minute = int(items[4])%100
            if hour==24:
                hour = 0
                yday = yday+1
            return datetime(year, 1, 1, hour, minute) + timedelta(yday-1)
        except StandardError:
            self.raise_error(line, 'parse error or invalid date')

    def extract_value_and_flags(self, line, seq):
        try:
            item = line.split(',')[seq+4].strip()
        except IndexError:
            raise ValueError()
        if self.nullstr:
            if item==self.nullstr:
                item = float('NaN')
        return (item, '')

    def subset_identifiers_match(self, line):
        si = line.split(',')[0].strip()
        return si==self.subset_identifiers


class Datafile_CR1000(Datafile):

    def extract_date(self, line):
        try:
            datestr = line.split(',')[0].strip('"')
            return datetime_from_iso(datestr[:16])
        except StandardError:
            self.raise_error(line, 'parse error or invalid date')

    def extract_value_and_flags(self, line, seq):
        return (line.split(',')[seq+3].strip(), '')

    def subset_identifiers_match(self, line):
        si = line.split(',')[2].strip()
        return si==self.subset_identifiers


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
            if len(datestr)<=10:
                datestr += ' ' + items[self.nfields_to_ignore + 1].strip('"')
                self.__separate_time = True
            return datetime.strptime(datestr, self.date_format).replace(
                        second=0) if self.date_format else datetime_from_iso(
                        datestr[:16])
        except ValueError as e:
            self.raise_error(line.strip(), "invalid date '{0}': {1}".format(
                    datestr, str(e)))

    def extract_value_and_flags(self, line, seq):
        index = self.nfields_to_ignore + seq + (
                                            1 if self.__separate_time else 0)
        value = line.split(self.delimiter)[index].strip()
        if self.nullstr and value==self.nullstr:
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
        value = line.split(self.delimiter)[seq+3]
        if self.nullstr:
            if value==self.nullstr:
                value = float('NaN')
        if not math.isnan(value):
            value = value.replace(self.decimal_separator, '.')
        return (value, '')

    def subset_identifiers_match(self, line):
        si = [x.strip() for x in line.split(self.delimiter)[0:3]]
        si1 = [x.strip() for x in self.subset_identifiers.split(',')]
        return si==si1

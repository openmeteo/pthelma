#!/usr/bin/python
"""
meteologger - utilities to read files of meteorological loggers

Copyright (C) 2005-2009 National Technical University of Athens
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

from datetime import datetime, timedelta
from xreverse import xreverse
from timeseries import Timeseries, datetime_from_iso, isoformat_nosecs

class Datafile:
    def __init__(self, db, datafiledict, logger=None):
        self.db = db
        self.filename = datafiledict['filename']
        self.datafile_fields = [int(x)
                            for x in datafiledict['datafile_fields'].split(',')]
        self.subset_identifiers = datafiledict.get('subset_identifiers', '')
        self.delimiter = datafiledict.get('delimiter', '')
        self.decimalseparator = datafiledict.get('decimalseparator', '')
        self.dateformat = datafiledict.get('dateformat', '')
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
    def _update_timeseries(self):
        c = self.db.cursor()
        try:
            c.execute(
                "SELECT TO_CHAR(timeseries_end_date(%d), 'YYYY-MM-DD HH24:MI')"
                % (self.ts))
            r = c.fetchone()
        finally:
            c.close()
        assert(r != None)
        self.logger.info('Last date in database: %s' % (str(r[0])))
        end_date = datetime(1, 1, 1)
        if r[0]: end_date = datetime_from_iso(r[0])
        if (not self.last_timeseries_end_date) or \
                                    end_date!=self.last_timeseries_end_date:
            self.last_timeseries_end_date = end_date
            self.logger.info('Reading datafile tail')
            self._get_tail()
            self.logger.info('%d lines in datafile tail' % (len(self.tail)))
            if len(self.tail)>0:
                self.logger.info('First date in datafile tail: %s' %
                (self.tail[0]['date'].isoformat(),))
        ts = Timeseries(self.ts)
        for line in self.tail:
            ts[isoformat_nosecs(line['date'])] = \
                self.extract_value_and_flags(line['line'], self.seq)
        self.logger.info('Appending %d records' % (len(ts)))
        if len(ts):
            self.logger.info('First appended record: %s' %
                            (ts.items()[0][0].isoformat()))
            self.logger.info('Last appended record:  %s' %
                            (ts.items()[-1][0].isoformat()))
            ts.append_to_db(self.db, commit=False)
    def _get_tail(self):
        "Read the part of the datafile after last_timeseries_end_date"
        self.tail = []
        xr = xreverse(self.fileobject, 2048)
        try:
            prev_date = ''
            while True:
                line = xr.next()
                self.logger.debug(line)
                if not self.subset_identifiers_match(line): continue
                date = self.extract_date(line)
                if date == prev_date:
                    self.logger.warning(
                       'WARNING: Omitting line with repeated date %s'
                       % (date))
                    continue
                prev_date = date
                self.logger.debug('Date: %s' % (date.isoformat()))
                if date <= self.last_timeseries_end_date:
                    break;
                self.tail.append({ 'date': date, 'line': line })
        except StopIteration:
            pass
        self.tail.reverse()
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
        raise RuntimeError, '%s: "%s": %s' % (self.filename, line, msg)

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
        return (line.split(',')[seq+4].strip(), '')
    def subset_identifiers_match(self, line):
        si = line.split(',')[0].strip()
        return si==self.subset_identifiers

class Datafile_lastem(Datafile):
    def extract_date(self, line):
        try:
            date = line.split(self.delimiter)[3]
            return datetime(*time.strptime(date, self.date_format)[:6])
        except StandardError:
            self.raise_error(line, 'parse error or invalid date')
    def extract_value_and_flags(self, line, seq):
        value = line.split(self.delimiter)[seq+3]
        value = value.replace(self.decimal_separator, '.')
        return (value, '')
    def subset_identifiers_match(self, line):
        si = [x.strip() for x in line.split(self.delimiter)[0:3]]
        si1 = [x.strip() for x in self.subset_identifiers.split(',')]
        return si==si1

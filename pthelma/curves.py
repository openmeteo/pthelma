#!/usr/bin/python
"""
curves - curves interpolations

Copyright (C) 2005-2011 National Technical University of Athens
Copyright (C) 2011 Stefanos Kozanis

Based on openmeteo.thelma.source.interpol.pas writen in
Pascal by A. Christofides, Stefanos Kozanis

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from math import log, exp
from datetime import datetime, MINYEAR, MAXYEAR
import fpconst
from ConfigParser import ParsingError
from pthelma.timeseries import Timeseries, datetime_from_iso

class CurvePoint(object):
    def __init__(self, independent, dependent):
        self.independent = independent
        self.dependent = dependent

    def  __eq__(self, other):
        return abs(self.dependent-other.dependent)<0.001 and\
               abs(self.independent-other.independent)<0001

    def __str__(self):
        return '(%f,%f)'%(self.independent, self.dependent,)

    def __repr__(self):
        return '(%f,%f)'%(self.independent, self.dependent,)

    def v(self, reverse=False):
        if reverse:
            return (self.dependent, self.independent)
        return (self.independent, self.dependent)

errFUNCIONTACCEPTSCURVEPOINT = 'Function accept only CurvePoint '+\
                               'object as argument'

class InterpolatingCurve(object):
    def __init__(self, logarithmic=False, offset=CurvePoint(0,0)):
        self.logarithmic = logarithmic
        self.offset = offset
        self.container = []

    def add(self, *args):
        if len(args) not in (1,2):
            raise TypeError('add() takes one or two arguments '
                            '(%d given)'%(len(args),))  
        if len(args)==1:
            if not isinstance(args[0], CurvePoint):
                raise TypeError(errFUNCIONTACCEPTSCURVEPOINT)
            point = args[0]
        else:
            point = CurvePoint(*args)
        self.container.append(point)

    def __str__(self):
        return str(self.container)

    def __repr__(self):
        return str(self.container)

    def __getitem__(self, key):
        return self.container[key]

    def __setitem__(self, key, value):
        if not isinstance(value, CurvePoint):
            raise TypeError(errFUNCIONTACCEPTSCURVEPOINT)
        self.container[key] = value

    def __delitem__(self, key):
        del(self.container[key])

    def __len__(self):
        return len(self.container)

    def __getslice__(self, i, j):
        return self.container[i:j]

    def __setslice__(self, i, j, sequence):
        for item in sequence:
            if not isinstance(item, CurvePoint):
                raise TypeError(errFUNCIONTACCEPTSCURVEPOINT)
        self.container[i:j] = sequence

    def __delslice__(self, i, j):
        del(self.container[i:j])

    def index(self, value):
        if not isinstance(value, CurvePoint):
            raise TypeError(errFUNCIONTACCEPTSCURVEPOINT)
        return self.container.index(value)

    def insert(self, i, value):
        if not isinstance(value, CurvePoint):
            raise TypeError(errFUNCIONTACCEPTSCURVEPOINT)
        self.container[i:i] = [value]

    def first(self):
        return self.container[0]

    def last(self):
        return self.container[len(self.container)-1]

    def value_over_curve(self, value, reverse=False):
        return value>self.last().v(reverse)[0]

    def value_in_curve_range(self, value, reverse=False):
        return value<=self.last().v(reverse)[0] and\
               value>=self.first().v(reverse)[0]

    def read_line(self, line, columns=(0,1)):
        values = [float(x) for x in line.split(',')]
        self.add(*[values[i] for i in columns])

    def read_fp(self, fp, columns=(0,1)):
        line = fp.readline()
        while line:
            if line.isspace(): break
            self.read_line(line, columns)
            line = fp.readline()

    def interpolate(self, value, reverse=False):
        if self.last().v(reverse)[0]>self.first().v(reverse)[0]:
            i = len(self)-2
            while i>=0:
                if self[i].v(reverse)[0]<value:
                    break
                i-=1
            i = max(i, 0)
        else:
            i = len(self)-2
            while i>=0:
                if self[i].v(reverse)[0]>value:
                    break
                i-=1
            i = max(i, 0)
        if self.logarithmic and self[i] == self.offset:
            i+=1
        if self.logarithmic and self[i+1] == self.offset:
            i-=1
        if self.logarithmic:
            x0, y0 = self.offset.v(reverse)[0], self.offset.v(reverse)[1]
        else:
            x0, y0 = 0,0
        x1 = self[i].v(reverse)[0]+x0
        x2 = self[i+1].v(reverse)[0]+x0
        x  = value+x0
        y1 = self[i].v(reverse)[1]+y0
        y2 = self[i+1].v(reverse)[1]+y0
        if self.logarithmic:
            try:
                if x>0:
                    return exp( (log(x)-log(x1))/(log(x2)-log(x1))*\
                                (log(y2)-log(y1)) + log(y1)) - y0
                else:
                    return fpconst.NaN
        else:
            return (x-x1)/(x2-x1)*(y2-y1)+y1

    def reverseinterpolate(self, value):
        return self.interpolate(value, True)

MINDATE = datetime(MINYEAR, 1, 1, 0, 0, 0)
MAXDATE = datetime(MAXYEAR, 12, 31, 0, 0, 0)

def read_meta_line(fp):
    """Read one line from a file format header and return a (name, value)
    tuple, where name is lowercased. Returns ('', '') if the next line is
    blank. Raises ParsingError if next line in fp is not a valid header
    line."""
    line = fp.readline()
    (name, value) = '', ''
    if line.isspace(): return (name, value)
    if line.find('=') > 0:
        (name, value) = line.split('=', 1)
        name = name.rstrip().lower()
        value = value.strip()
    for c in name:
        if c.isspace():
            name = ''
            break
    if not name:
        raise ParsingError(("Invalid file header line"))
    return (name, value)

class TransientCurve(InterpolatingCurve):
    def __init__(self, logarithmic=False, offset=CurvePoint(0,0),
                 extension_line=False,
                 start_date=MINDATE, end_date=MAXDATE):
        super(TransientCurve, self).__init__(logarithmic, offset)
        self.start_date = start_date
        self.end_date = end_date
        self.extension_line=extension_line

    def read_fp(self, fp, columns=(0,1)):
        (name, value) = read_meta_line(fp)
        while name:
            if name=='extension':
                self.extension_line = str.lower(value)=='true'
            elif name=='logarithmic':
                self.logarithmic = str.lower(value)=='true'
            elif name=='offset':
                self.offset=CurvePoint(float(value),0)
            elif name in ('start_date', 'startdate'):
                self.start_date=datetime_from_iso(value)
            elif name in ('end_date', 'enddate'):
                self.end_date=datetime_from_iso(value)
            (name, value) = read_meta_line(fp)
        super(TransientCurve, self).read_fp(fp, columns)

class NoInterpolCurveError(Exception): pass

errFUNCIONTACCEPTSCURVE = 'Function accept only Transient Curve '+\
                          'object as argument'

class TransientCurveList(object):
    def __init__(self):
        self.container = []

    def addcurve(self, curve):
        if not isinstance(curve, TransientCurve):
            raise TypeError(errFUNCIONTACCEPTSCURVE)
        self.container.append(curve)

    def add(self, logarithmic=False, offset=CurvePoint(0,0),
                 extension_line=False,
                 start_date=MINDATE, end_date=MAXDATE):
        curve = TransientCurve(logarithmic, offset, extension_line,
                               start_date, end_date)
        self.addcurve(curve)

    def __str__(self):
        return str(self.container)

    def __repr__(self):
        return str(self.container)

    def __getitem__(self, key):
        return self.container[key]

    def __setitem__(self, key, value):
        if not isinstance(value, TransientCurve):
            raise TypeError(errFUNCIONTACCEPTSCURVE)
        self.container[key] = value

    def __delitem__(self, key):
        del(self.container[key])

    def __len__(self):
        return len(self.container)

    def __getslice__(self, i, j):
        return self.container[i:j]

    def __setslice__(self, i, j, sequence):
        for item in sequence:
            if not isinstance(item, TransientCurve):
                raise TypeError(errFUNCIONTACCEPTSCURVE)
        self.container[i:j] = sequence

    def __delslice__(self, i, j):
        del(self.container[i:j])

    def index(self, value):
        if not isinstance(value, TransientCurve):
            raise TypeError(errFUNCIONTACCEPTSCURVE)
        return self.container.index(value)

    def insert(self, i, value):
        if not isinstance(value, TransientCurve):
            raise TypeError(errFUNCIONTACCEPTSCURVE)
        self.container[i:i] = [value]

    def first(self):
        return self.container[0]

    def last(self):
        return self.container[len(self.container)-1]

    def find(self, date, extension_line=False):
        for curve in self.container:
            if date>=curve.start_date and date<=curve.end_date and\
               extension_line==curve.extension_line:
                return curve
        raise NoInterpolCurveError('No interpolation curve for '
                                   'date %s, with extension '
                                   'line=%s'%(date, extension_line,))

    def has_extension_lines(self):
        for curve in self.container:
            if curve.extension_line:
                return True
        return False

    def interpolate(self, date, value):
        if not self.has_extension_lines():
            return self.find(date).interpolate(value)
        normal_curve = self.find(date)
        ext_curve = self.find(date, True)
        if not normal_curve.value_over_curve(value):
            return normal_curve.interpolate(value)
        if ext_curve.value_in_curve_range(value) or \
                    ext_curve.value_over_curve(value):
            return ext_curve.interpolate(value)
        curve = InterpolatingCurve(logarithmic =\
                                            normal_curve.logarithmic,
                                   offset = normal_curve.offset)
        curve[0:2] = [normal_curve.last(), ext_curve.first()]
        return curve.interpolate(value)

    def interpolate_ts(self, timeseries):
        result = Timeseries(time_step=timeseries.time_step)
        for date in timeseries.iterkeys():
            value = timeseries[date]
            if fpconst.isNaN(value):
                result[date] = fpconst.NaN
            else:
                result[date] = self.interpolate(date, value)
        return result

    def read_fp(self, fp):
        (name, value) = read_meta_line(fp)
        while name:
            if name=='count': count = int(value)
            (name, value) = read_meta_line(fp)
        while count>0:
            self.add()
            self.last().read_fp(fp)
            count-=1


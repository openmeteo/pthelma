#!/usr/bin/python
"""
Datetime list
=====================

Copyright (C) 2005-2012 National Technical University of Athens

Copyright (C) 2005 Antonis Christofides, 2012 Stefanos Kozanis

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from datetime import datetime
from ctypes import CDLL, c_int, c_longlong,  c_char_p, byref, \
                   c_void_p
import platform

import iso8601

from pthelma.timeseries import (isoformat_nosecs,
    _DT_BASE, _datetime_to_time_t, _time_t_to_datetime,)

dickinson = CDLL(
    (platform.system() == 'Windows' and 'dickinson.dll') or
    (platform.system().startswith('Darwin') and 'libdickinson.dylib') or
    'libdickinson.so')

dickinson.dl_get_item.restype = c_longlong
dickinson.dl_create.restype = c_void_p

class DatetimeList(list):

    def __init__(self, *args):
        self.dl_handle=None
        self.dl_handle = c_void_p(dickinson.dl_create())
        if self.dl_handle.value==0:
            raise MemoryError.Create('Could not allocate memory '
                                     'for date time list object')
        self.__dickinson = dickinson
        if len(args)>0:
            for item in args:
                self.append(item)

    def __del__(self):
        if self.dl_handle is None:
            return
        if self.dl_handle.value!=0:
            self.__dickinson.dl_free(self.dl_handle)
        self.dl_handle.value=0

    def append(self, x):
        d = iso8601.parse_date(x, default_timezone=None) \
            if (isinstance(x, unicode) or isinstance(x, str)) else x
        if not isinstance(d, datetime):
            raise ValueError('Only date time items or ISO date strings '
                             'allowed for date time lists') 
        err_str_c = c_char_p()
        index_c = c_int()
        err_no_c = dickinson.dl_insert_record(self.dl_handle,
            c_longlong(_datetime_to_time_t(d)),
            byref(index_c), byref(err_str_c))
        if err_no_c!=0:
            raise Exception('Something wrong occured in dickinson '
                'function when setting a time series value. '+
                'Error message: '+repr(err_str_c.value))

    def insert(self, x):
        return self.append(x)

    def __repr__(self):
        return '[%s]'%(', '.join((repr(i) for i in self)),)

    def __str__(self):
        return '[%s]'%(', '.join((str(i) for i in self)),)

    def items(self):
        return [i for i in self]

    def __len__(self):
        return dickinson.dl_length(self.dl_handle)

    def __delitem__(self, key):
        if not isinstance(key, int):
            raise KeyError('Index is not an integer')
        if key<0 or key>self.__len__()-1:
            raise IndexError('Index out of bounds (%d)'%key)
        dickinson.dl_delete_item(self.dl_handle, c_int(key))

    def pop(self, *args):
        if self.__len__()<1:
            raise IndexError('Empty datetime list, cannot pop')
        key = args[0] if len(args)!=0 else self.__len__()-1
        if not isinstance(key, int):
            raise KeyError('Pop index is not an integer')
        if key<0 or key>self.__len__()-1:
            raise IndexError('Index out of bounds (%d)'%key)
        result = self.__getitem__(key)
        dickinson.dl_delete_item(self.dl_handle, c_int(key))
        return result

    def __contains__(self, item):
        index_c = dickinson.dl_get_i(self.dl_handle,
                                        c_longlong(_datetime_to_time_t(item)))
        return False if index_c<0 else True

    def __getitem__(self, key):
        if not isinstance(key, int):
            raise KeyError('Invalid key: %s'%(key,))
        if key<0 or key>self.__len__()-1:
            raise IndexError('Index out of bounds (%d)'%(key,))
        return _time_t_to_datetime(dickinson.dl_get_item(self.dl_handle,
               c_int(key)))

    def iterkeys(self):
        i = 0
        while i<self.__len__():
            yield self[i]
            i+=1
    __iter__ = iterkeys

    def __reversed__(self):
        i = self.__len__()-1
        while i>=0:
            yield self[i]
            i-=1

    def clear(self):
        i = self.__len__()-1
        while i>=0:
            dickinson.dl_delete_item(self.dl_handle, i)
            i-=1

    def index(self, x):
        d = iso8601.parse_date(x, default_timezone=None) \
            if (isinstance(x, unicode) or isinstance(x, str)) else x
        if not isinstance(d, datetime):
            raise ValueError('Only date time items or ISO date strings '
                             'allowed for date time lists') 
        err_str_c = c_char_p()
        index_c = c_int()
        timestamp_c = c_longlong(_datetime_to_time_t(d))
        pos = dickinson.dl_get_i(self.dl_handle, timestamp_c)
        if pos<0:
            raise KeyError('No such item (%s) in date time list'%\
                           (x,))
        return pos

    def sort(self):
        pass

    def count(self, x):
        return 1 if x in self else 0

    def remove(self, x):
        pos = self.index(x)
        self.__delitem__(pos)

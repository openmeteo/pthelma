=========
aggregate
=========

-----------------------
Time series aggregation
-----------------------

:Manual section: 1

SYNOPSIS
========

``aggregate [--traceback] config_file``

DESCRIPTION AND QUICK START
===========================

``aggregate`` gets the data of time series from files and creates time
series of a larger time step, storing the result in files.  The
details of its operation are specified in the configuration file
specified on the command line.

Installation
------------

To install ``aggregate``, see :ref:`install`.

How to run it
-------------

First, you need to create a configuration file with a text editor such
as ``vim``, ``emacs``, ``notepad``, or whatever. Create such a file
and name it, for example, :file:`/var/tmp/aggregate.conf`, or, on
Windows, something like :file:`C:\\Users\\user\\aggregate.conf`, with
the following contents (the contents don't matter at this stage, just
copy and paste them from below)::

    [General]
    loglevel = INFO

Then, open a command prompt and give it this command:

**Unix/Linux**::

    aggregate /var/tmp/aggregate.conf

**Windows**::

    C:\Program Files\Pthelma\aggregate.exe C:\Users\user\aggregate.conf

(the details may differ; for example, in 64-bit Windows, it may be
:file:`C:\\Program Files (x86)` instead of :file:`C:\\Program Files`.)

If you have done everything correctly, it should output an error message
complaining that something in its configuration file isn't right.

Configuration file example
--------------------------

Take a look at the following example configuration file and read the
explanatory comments that follow it:

.. code-block:: ini

    [General]
    loglevel = INFO
    logfile = C:\Somewhere\aggregate.log
    base_dir = C:\Somewhere
    target_step = 60,0

    [temperature]
    source_file = temperature-10min.hts
    target_file = temperature-hourly.hts
    interval_type = average

    [rainfall]
    source_file = rainfall-10min.hts
    target_file = rainfall-hourly.hts
    interval_type = sum

With the above configuration file, ``aggregate`` will log information in
the file specified by :confval:`logfile`. It will aggregate the
specified time series into hourly (60 minutes, 0 months). The
filenames specified with :confval:`source_file` and
:confval:`target_file` are relative to :confval:`base_dir`. For the
temperature, source records will be averaged, whereas for rainfall
they will be summed.

CONFIGURATION FILE REFERENCE
============================

The configuration file has the format of INI files. There is a
``[General]`` section with general parameters, and any number of other
sections, which we will call "time series sections", each time series
section referring to one time series.

General parameters
------------------

.. confval:: loglevel

   Optional. Can have the values ``ERROR``, ``WARNING``, ``INFO``,
   ``DEBUG``.  The default is ``WARNING``.

.. confval:: logfile

   Optional. The full pathname of a log file. If unspecified, log
   messages will go to the standard error.

.. confval:: base_dir

   Optional. ``aggregate`` will change directory to this directory, so
   any relative filenames will be relative to this directory. If
   unspecified, relative filenames will be relative to the directory
   from which ``aggregate`` was started.

.. confval:: target_step

   A pair of integers indicating the number of minutes and months in
   the target time step. One and only one of these numbers must be
   nonzero (i.e. the target time step is an integer number of minutes
   or months).

.. confval:: nominal_offset

   Optional. A pair of integers. The default is 0, 0. The timestamps
   of, e.g., an hourly time series usually end in :00, but they could
   end in, say, :07. This is a nominal offset of 7 minutes. A nominal
   offset for months is usually only used to specify a hydrological
   year, e.g. hydrological years in Greece have a nominal offset of 9
   months.

   This parameter specifies the nominal offset for the target time
   series.

.. confval:: actual_offset

   Optional. A pair of integers. The default is 0, 0. Usually the
   timestamps refer to the interval whose time ends at the timestamp.
   So, for example, in an hourly time series (with a nominal_offset of
   50), 2014-06-16 15:50 refers to the interval 2014-06-16
   14:50-15:50.

   In some rare cases, however, we may want to use the timestamp
   2014-06-16 15:50 to signify the interval 2014-06-16 14:45-15:45. In
   that case, we say we have an actual offset of -5 minutes.

   There are two use cases for this. One is river flows. Suppose you
   are aggregating hourly river stages into monthly river stages. If
   your basin is such that a rainfall today results in increased stage
   2 days later, you may want "April 2014" for stages to actually mean
   the period "3 April to 3 May 2014", so that it correlates better
   with monthly rainfalls. In this case, you have an actual offset of
   2880 minutes (plus one month, see below).

   The second use case is when the timestamp indicates the beginning
   rather than the end of the interval, which is usually the case for
   monthly and annual time series. For a monthly time series, the
   timestamp 2003-11-01 00:00 (normally rendered as 2003-11) usually
   denotes the interval that starts at the beginning of November and
   ends at the end of November. In these cases, the actual offset
   should be the length of the interval, i.e. 1 month for monthly time
   series and 12 months for annual time series.

   Both minutes and months can be nonzero. In the river flows example
   above, the actual offset would be (2880, 1).

.. confval:: missing_allowed
             missing_flag

   Optional, default 0. If some of the source records corresponding to
   a destination record are missing, :confval:`missing_allowed`
   specifies what will be done. If the ratio of missing values to
   existing values in the source record is greater than
   :confval:`missing_allowed`, the resulting destination record is
   null; otherwise, the destination record is derived even though some
   records are missing. In that case, the flag specified by
   :confval:`missing_flag` is raised in the destination record.

Time series sections
--------------------

The name of the section is ignored.

.. confval:: source_file

   The filename of the source file with the time series, in :ref:`file
   format <fileformat>`; it must be absolute or relative to
   :confval:`base_dir`.

.. confval:: target_file

   The filename of the target file, which will be written in
   :ref:`file format <fileformat>`; it must be absolute or relative to
   :confval:`base_dir`. In this version of ``aggregate``, all the
   aggregation is repeated even if it or part of it has been done in
   the past, and the file is entirely overwritten if it already
   exists.

.. confval:: interval_type

   How the aggregation will be performed; one of "average", "sum",
   "maximum", "minimum", or "vector_average". In the last case, each
   produced record is the direction in degrees of the sum of the unit
   vectors whose direction is specified by the source records.

AUTHOR AND COPYRIGHT
====================

``aggregate`` was written by Antonis Christofides,
anthony@itia.ntua.gr.

| Copyright (C) 2014 TEI of Epirus

``aggregate`` is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

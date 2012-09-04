==========
loggertodb
==========

------------------------------------------------------------
insert automatic meteorological station data to the database
------------------------------------------------------------

:Manual section: 1

SYNOPSIS
========

``loggertodb config_file``

DESCRIPTION
===========

``loggertodb`` reads a plain text data file, connects to the enhydris
database, determines which records in the file are newer than those
stored in the database, and stores them in the database. The details
of its operation are specified in the configuration file specified on
the command line.

CONFIGURATION FILE
==================

The configuration file has the format of INI files. There is a
``[General]`` section with general parameters, and any number of other
sections, which we will call "file sections", each file section
referring to one file to be processed; this makes it possible to
process many files in a single ``loggertodb`` execution using a single
configuration file and a single database connection.

General parameters
------------------

loglevel
   Can have the values ``ERROR``, ``WARNING``, ``INFO``, ``DEBUG``,
   indicating the amount of output requested from ``loggertodb``. The
   default is ``WARNING``.

logfile
   The full pathname of a log file. If unspecified, log messages will
   go to the standard error.

host, dbname, user, password
   The server name, database name, user name and password with which
   ``loggertodb`` will connect.  The user must have write permissions
   for all time series specified in the ``datafile_fields`` parameter.

all_or_nothing
   Normally ``loggertodb`` commits the transaction after each file is
   processed. If ``all_or_nothing`` is set to true, it will process
   all files in a single transaction.

no_commit
   If this is specified and is true, then the changes will be rolled
   back. Use this in combination with ``loglevel=INFO`` for testing
   and debugging, when you do not want your database to be changed.

File parameters
---------------

filename
   The full pathname of the data file.

datafile_format
   The format of the datafile. See `SUPPORTED FORMATS`_.

datafile_fields
   A series of comma-separated integers representing the ids of the
   time series to which the data file fields correspond; a zero
   indicates that the field is to be ignored. The first number
   corresponds to the first field after the date (and other fixed
   fields depending on data file format, such as the subset
   identifier) and should be the id of the corresponding time series,
   or zero if the field is dummy; the second number corresponds to the
   second field after the fixed fields, and so on.

subset_identifiers
   Some file formats mix two or more sets of measurements in the same
   file; for example, there may be ten-minute and hourly measurements
   in the same file, and for every 6 lines with ten-minute
   measurements there may be an additional line with hourly
   measurements (not necessarily the same variables). ``loggertodb``
   processes only one set of lines each time. Such files have one or
   more additional distinguishing fields in each line, which helps to
   distinguish which set it is.  ``subset_identifiers``, if present,
   is a comma-separated list of identifiers, and will cause
   ``loggertodb`` to ignore lines with different subset identifiers.
   (Which fields are the subset identifiers depends on the data file
   format.)

delimiter, decimal_separator, date_format
   Some file formats may be dependent upon regional settings; these
   formats support ``delimiter``, ``decimal_separator``, and
   ``date_format``.  ``date_format`` is specified in the same way as for
   `strftime(3)`_.
   
   .. _strftime(3): http://docs.python.org/lib/module-time.html

SUPPORTED FORMATS
=================

The following formats are currently supported: 

simple
   The ``simple`` format is comma-delimited lines of which the first
   field is the date and time in ISO8601 format, and the rest of the
   fields hold time series values. The date can use a space instead of
   ``T`` as the date/time separator, it can include seconds, which are
   ignored, and it can optionally be enclosed in double quotation
   marks.

CR2000
   The ``CR2000`` format is like ``simple``, but the first two fields
   after the date are ignored (they are a record number and a station
   id).

CR1000
   This is similar to ``CR2000``, but uses subset identifiers in the
   third field. It is not clear whether it is debugged and works
   properly, neither whether its features are a matter of different
   data logger model or different data logger configuration.

deltacom
   The ``deltacom`` format is space-delimited lines of which the first
   field is the date and time in ISO8601 format ``YYYY-MM-DDTHH:mm``,
   and the rest of the fields are either dummy or hold time series
   values.

lastem
   The ``lastem`` format is dependent on regional settings, and uses
   the ``delimiter``, ``decimal_separator``, and ``date_format``
   parameters.  It is lines delimited with the specified delimiter, of
   which the first three fields are the subset identifiers, the fourth
   is the date, and the rest are either dummy or hold time series
   values.

pc208w
   The ``pc208w`` format is comma-delimited items in the following
   order: subset identifier, logger id (ignored), year, day of year,
   time in ``HHmm``, measurements.

zeno
   The ``zeno`` format is space-delimited items in the following
   order: date in ``yy/mm/dd`` format, time in ``HH:mm`` format,
   measurements.

xyz
   The ``xyz`` format is whitespace-delimited items in the following
   order: date in ``dd/mm/yyyy`` format, time in ``HH:mm:ss`` format,
   measurements.

OPERATION DETAILS
=================

``loggertodb`` connects to the server and gets the end date for each
time series specified in the ``datafilefields`` parameter. It then
picks up a time series id, scans the data file, determines which is
the first record of that time series not already stored in the
database, and appends that record and all subsequent records to the
database. It does this for all time series specified in
``datafilefields``.

AUTHOR, COPYRIGHT, HISTORY
==========================

``loggertodb`` was written by Antonis Christofides,
anthony@itia.ntua.gr.  It is derived from ``autoupdate``, also written
by Antonis Christofides, for the old openmeteo.org database.
``loggertodb`` is essentially ``autoupdate`` adapted to the hydria
database for the Odysseus project, and later to the enhydris database.
This version of ``loggertodb`` has nothing to do with versions prior
to 1.0.0, which were completely different, in a different programming
language (Perl rather than Python), and not based on ``autoupdate``.

Copyright (C) 2005-2012 National Technical University of Athens

Copyright (C) 2004 Antonis Christofides.

``loggertodb`` is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

=====
Usage
=====

Synopsis
========

``spatialize [--traceback] config_file``

Description and quick start
===========================

``spatialize`` gets the data of time series from files and performs
spatial integration, storing the result in ``tif`` files.  The details
of its operation are specified in the configuration file specified on
the command line.

How to run it
-------------

First, you need to create a configuration file with a text editor such
as ``vim``, ``emacs``, ``notepad``, or whatever. Create such a file
and name it, for example, :file:`/var/tmp/spatialize.conf`, with
the following contents (the contents don't matter at this stage, just
copy and paste them from below):

.. code-block:: ini

    loglevel = INFO

Then, open a command prompt and give it this command::

    spatialize /var/tmp/spatialize.conf

If you have done everything correctly, it should output an error message
complaining that something in its configuration file isn't right.

Configuration file example
--------------------------

Take a look at the following example configuration file and read the
explanatory comments that follow it:

.. code-block:: ini

    loglevel = INFO
    logfile = /var/log/spatialize.log
    mask = /etc/hspatial/mask.tif
    epsg = 2100
    output_dir = /var/opt/hspatial
    filename_prefix = rainfall
    number_of_output_files = 24
    method = idw
    alpha = 1
    files = /var/opt/timeseries/inputfile1.hts
            /var/opt/timeseries/inputfile2.hts
            /var/opt/timeseries/inputfile3.hts

With the above configuration file, ``spatialize`` will log information
in the file specified by :confval:`logfile`.  :confval:`mask` defines
the study area, whose co-ordinates are in the reference system
specified by :confval:`epsg`.  The output is GeoTIFF files in
:confval:`output_dir`, prefixed with :confval:`filename_prefix`. In
this example, the output files will be named something like
:file:`/var/opt/hspatial/rainfall-2014-04-29-15-00.tif`.  Only the most
recent 24 (:confval:`number_of_output_files`) output
files will be kept, and older ones will automatically be deleted;
these 24 files will be recreated if missing. The integration method
will be :confval:`idw` with :confval:`alpha` = 1.  The spatial
integration will be performed given the three time series specified in
:confval:`files`.

Configuration file reference
============================

The configuration file has the format of INI files, but without
sections.

Parameters
----------

.. confval:: loglevel

   Optional. Can have the values ``ERROR``, ``WARNING``, ``INFO``, ``DEBUG``.
   The default is ``WARNING``.

.. confval:: logfile

   Optional. The full pathname of a log file. If unspecified, log
   messages will go to the standard error.

.. confval:: mask

   A GeoTIFF file defining the study area. It must contain a single
   band, whose nonzero cells comprise the area. ``spatialize`` will
   interpolate a value in each of these cells.

.. confval:: epsg

   An integer specifying the co-ordinate reference system (CRS) used
   by :confval:`mask`. ``spatialize`` will transform the co-ordinates of
   the stations to that CRS before performing the integration.

.. confval:: output_dir
             filename_prefix

   Output files are GeoTIFF files placed in :confval:`output_dir` and
   having the specified :confval:`filename_prefix`. After the prefix
   there follows a hyphen and then the date in format
   YYYY-MM-DD-HH-mm, however some parts of the date may be missing;
   for daily time series, the hour and minutes are missing; for
   monthly, the date is also missing; for annual, the month is also
   missing.

   These GeoTIFF files contain a single band with the calculated
   result. 
   
.. confval:: number_of_output_files

   The number of files to produce and keep. ``spatialize`` performs
   spatial integration for the last available timestamp, for the
   last-but-one, and so on, until there are
   :confval:`number_of_output_files` files (or less if the time series
   don't have enough records). If any files already exist, they are
   not recalculated. Older files in excess of
   :confval:`number_of_output_files` are deleted.

.. confval:: method
             alpha

   The interpolation method. Currently only idw is allowed, but
   hopefully in the future there will also be kriging. If the method
   is idw, the parameter :confval:`alpha` can optionally be specified
   (default 1).

.. confval:: files

   The files containing the time series; these must be in `file
   format`_, including Location and Time_step headers.

.. _file format: https://github.com/openmeteo/htimeseries#file-format

Author and copyright
====================

``spatialize`` was written by Antonis Christofides,
anthony@itia.ntua.gr.

| Copyright (C) 2014 TEI of Epirus
| Copyright (C) 2019 University of Ioannina

``spatialize`` is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

=====
bitia
=====

-----------------------------------------
Spatial integration of point measurements
-----------------------------------------

:Manual section: 1

SYNOPSIS
========

``bitia [--traceback] config_file``

DESCRIPTION AND QUICK START
===========================

``bitia`` gets the data of time series from an Enhydris database and performs
spatial integration, storing the result in ``tif`` files.  The details of its
operation are specified in the configuration file specified on the command
line.

Installation
------------

To install ``bitia``, see :ref:`install`.

How to run it
-------------

First, you need to create a configuration file with a text editor such
as ``vim``, ``emacs``, ``notepad``, or whatever. Create such a file
and name it, for example, :file:`/var/tmp/bitia.conf`, or, on
Windows, something like :file:`C:\\Users\\user\\bitia.conf` , with
the following contents (the contents don't matter at this stage, just
copy and paste them from below):

    [General]
    loglevel = INFO

Then, open a command prompt and give it this command:

**Unix/Linux**::

    bitia /var/tmp/bitia.conf

**Windows**::

    C:\Program Files\Pthelma\bitia.exe C:\Users\user\bitia.conf

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
    logfile = C:\Somewhere\bitia.log
    mask = C:\Somewhere\mask.tif
    epsg = 2100
    cache_dir = C:\Somewhere\BitiaCache
    output_dir = C:\Somewhere\BitiaOutput
    filename_prefix = rainfall
    files_to_produce = 24
    method = idw
    alpha = 1

    [ntua]
    base_url = https://openmeteo.org/
    id = 6539

    [nedontas]
    base_url = https://openmeteo.org/
    id = 9356

    [arta]
    base_url = https://upatras.gr/enhydris/
    user = george
    password = topsecret
    id = 8765

With the above configuration file, ``bitia`` will log information in
the file specified by :confval:`logfile`.  :confval:`mask` defines the
study area, whose co-ordinates are in the reference system specified
by :confval:`epsg`.  ``bitia`` downloads time series and some other
stuff from Enhydris, and caches it in files in :confval:`cache_dir`.
Its output is GeoTIFF files in :confval:`output_dir`, prefixed with
:confval:`filename_prefix`. In this example, the output files will be
named :file:`C:\\Somewhere\\BitiaOutput\\rainfall-XXXX.tif`, where
XXXX is from 0000 to 0023. 24 output files will be produced in total
(:confval:`files_to_produce`), and the old ones will be removed.  The
file ending in 0000 will correspond to the latest time available from
the data; the one ending in 0001 will correspond to one time step
before; and so on. The files will be renamed if new data becomes
available, and missing ones will be recreated.  The integration method
will be :confval:`idw` with :confval:`alpha` = 1.

The spatial integration will be performed given three time series
("ntua", "nedontas" and "arta"), whose :confval:`base_url` and
:confval:`id` must be given.  Some Enhydris installations may require
a :confval:`user` and a :confval:`password` to access the data.

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

.. confval:: mask

   A GeoTIFF file defining the study area. It must contain a single
   band, whose nonzero cells comprise the area. ``bitia`` will
   interpolate a value in each of these cells.

.. confval:: epsg

   An integer specifying the co-ordinate reference system (CRS) used
   by :confval:`mask`. ``bitia`` will transform the co-ordinates of
   the stations to that CRS before performing the integration.

.. confval:: cache_dir

   The directory in which data downloaded from Enhydris will be
   cached. This is time series data plus some minor information such
   as the location of the stations to which these measurements refer
   and the time series step.

.. confval:: output_dir
             filename_prefix

   Output files are GeoTIFF files placed in :confval:`output_dir` and
   having the specified :confval:`filename_prefix`. After the prefix
   there follows a hyphen and four digits.

   These GeoTIFF files contain a single band with the calculated
   result. 
   
.. confval:: files_to_produce

   The number of files to produce. ``bitia`` performs spatial
   integration for the last available timestamp, for the last-but-one,
   and so on, until there are :confval:`files_to_produce` files (or
   less if the time series don't have enough records). If any files
   already exist, they are not recalculated. Old files in excess of
   :confval:`files_to_produce` are deleted.

.. confval:: method
             alpha

   The interpolation method. Currently only idw is allowed, but
   hopefully in the future there will also be kriging. If the method
   is idw, the parameter :confval:`alpha` can optionally be specified
   (default 1).

Time series sections
--------------------

All specified time series must have the same time step. The name of
the section is ignored.

.. confval:: base_url

   The base URL of the Enhydris installation that hosts the time
   series.  Most often the :confval:`base_url` will be the same for
   all time series, but in the general case you might want to get data
   from many Enhydris installations.

.. confval:: id

   The id of the time series.

.. confval:: user
             password

   Optional.  Needed if that Enhydris installation needs login in
   order to provide access to the data.

AUTHOR AND COPYRIGHT
====================

``bitia`` was written by Antonis Christofides,
anthony@itia.ntua.gr.

| Copyright (C) 2014 TEI of Epirus

``bitia`` is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

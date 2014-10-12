=======
gerarda
=======

-----------------------
Evaporation calculation
-----------------------

:Manual section: 1

SYNOPSIS
========

``gerarda [--traceback] config_file``

DESCRIPTION AND QUICK START
===========================

``gerarda`` reads GeoTIFF files with temperature, humidity, solar
radiation, pressure and wind speed, and produces a GeoTIFF file with
evapotranspiration calculated with the Penman-Monteith method. The
details of its operation are specified in the configuration file
specified on the command line.

The methodology used is that of Allen et al. (1998).  Details can be
found in :ref:`evaporation` and in the code itself, which has comments
indicating which equations it uses.

Installation
------------

To install ``gerarda``, see :ref:`install`.

How to run it
-------------

First, you need to create a configuration file with a text editor such
as ``vim``, ``emacs``, ``notepad``, or whatever. Create such a file
and name it, for example, :file:`/var/tmp/gerarda.conf`, or, on
Windows, something like :file:`C:\\Users\\user\\gerarda.conf`, with
the following contents (the contents don't matter at this stage, just
copy and paste them from below)::

    [General]
    loglevel = INFO

Then, open a command prompt and give it this command:

**Unix/Linux**::

    gerarda /var/tmp/gerarda.conf

**Windows**::

    C:\Program Files\Pthelma\gerarda.exe C:\Users\user\gerarda.conf

(the details may differ; for example, in 64-bit Windows, it may be
:file:`C:\\Program Files (x86)` instead of :file:`C:\\Program Files`.)

If you have done everything correctly, it should output an error message
complaining that something in its configuration file isn't right.

Configuration file example
--------------------------

Take a look at the following example configuration file and read the
explanatory comments that follow it:

.. code-block:: ini

   loglevel = INFO
   logfile = C:\Somewhere\gerarda.log
   base_dir = C:\Somewhere
   albedo = 0.23
   nighttime_solar_radiation_ratio = 0.8
   elevation = 8
   step_length = 60
   unit_converter_pressure = x / 10.0
   unit_converter_solar_radiation = x * 3600 / 1e6

With the above configuration file, ``gerarda`` will log information in
the file specified by :confval:`logfile`. It will calculate hourly
evaporation (:confval:`step_length`) at the specified
:confval:`elevation` with the specified :confval:`albedo` and
:confval:`nighttime_solar_radiation_ratio` (these three parameters can
be GeoTIFF files instead of numbers). For some variables, the input
files are in different units than the default ones (hPa instead of kPa
for pressure, W/m² instead of MJ/m²/h for solar radiation) and need to
be converted (:confval:`unit_converter`). The calculation is performed
once for each one of the sets of files that are in
:confval:`base_dir`; for example, if inside `base_dir` there are files
`temperature-2014-10-12-18-00+0200.tif`,
`humidity-2014-10-12-18-00+0200.tif`, and so on (including variables
named `wind_speed`, `pressure`, and `solar_radiation`), there will be
a resulting file `evaporation-2014-10-12-18-00+0200.tif`; if there are
files for other dates, there will be a result for them as well.  The
calculation is performed only if the resulting file does not already
exist, or if at least one of the input files has a later modification
time.  If there are any `evaporation-....tif` files without
corresponding input files, they will be deleted.

CONFIGURATION FILE REFERENCE
============================

The configuration file has the format of INI files, but without
sections.

Parameters
----------

.. confval:: loglevel

   Optional. Can have the values ``ERROR``, ``WARNING``, ``INFO``,
   ``DEBUG``.  The default is ``WARNING``.

.. confval:: logfile

   Optional. The full pathname of a log file. If unspecified, log
   messages will go to the standard error.

.. confval:: base_dir

   The directory in which ``gerarda`` will look for input files and
   write output files.  If unspecified, it is the directory from which
   ``gerarda`` was started.

.. confval:: step_length

   An integer indicating the number of minutes in
   the time step. In this version, ``gerarda`` can only handle hourly
   time steps or smaller.

.. confval:: elevation

   Meters of the location above sea level; this can be either a number
   or a GeoTIFF file with a digital elevation model.

.. confval:: nighttime_solar_radiation_ratio

   In order to estimate the outgoing radiation, the ratio of incoming
   solar radiation to clear sky solar radiation is used as a
   representation of cloud cover. This, however, does not work during
   the night, in which case :confval:`nighttime_solar_radiation_ratio`
   is used as a rough approximation of that ratio. It should be a
   number between 0.4 and 0.8; see Allen et al. (1998), top of page
   75. It can be a number or a GeoTIFF file.

.. confval:: albedo

   A number between 0 and 1 or a GeoTIFF file with such numbers. It
   can also be a list of twelve space-separated numbers and/or GeoTIFF
   files, where the first is for January, the second for February, and
   so on. For example::

      albedo = albedo-jan.tif albedo-feb.tif albedo-mar.tif albedo-apr.tif
               albedo-may.tif albedo-jun.tif albedo-jul.tif albedo-aug.tif
               albedo-sep.tif 0.23           albedo-nov.tif albedo-dec.tif

   Note that in the configuration file long lines can be wrapped by
   indenting the additional lines. Also note that GeoTIFF files can be
   mixed with numbers; in the above example, GeoTIFF files are
   specified for all months except for October, which has a single
   value of 0.23.

   If a single number or GeoTIFF file is specified, it is used for all
   the year.

.. confval:: unit_converter

   The meteorological values that are supplied with the GeoTIFF files
   of the file set sections are supposed to be in the following units:

   ========================  =====================
   Parameter                 Unit
   ========================  =====================
   temperature               ℃
   humidity                  %
   wind speed                m/s
   pressure                  kPa
   solar radiation           MJ/m²/h
   ========================  =====================
   
   If they are in different units,
   :confval:`unit_converter_temperature`,
   :confval:`unit_converter_humidity`, and so on, are Python
   expressions that convert the given units to the above units; in
   these expressions, the symbol ``x`` refers to the given value. For
   example, if you have temperature in ℉, specify::
   
      unit_converter_temperature = (x - 32.0) * 5.0 / 9.0
      
   Use 32.0 rather than 32, and so on, in order to ensure that the
   calculations will be performed in floating point.

.. confval:: temperature_prefix
             humidity_prefix
             wind_speed_prefix
             pressure_prefix
             solar_radiation_prefix
             evaporation_prefix

   Optional. `gerarda` assumes that the input files are
   named :samp:`{variable}-{date}.tif`, where *variable* one of
   `temperature`, `humidity`, `wind_speed`, `pressure` and
   `solar_radiation`, and, similarly, for the output file *variable*
   is `evaporation`. With these parameters these names can be changed;
   for example::

      humidity_prefix = hum

   In that case, the humidity files are going to have a name similar
   to `hum-2014-10-12-18-00+0200.tif`.

REFERENCES
==========

R. G. Allen, L. S. Pereira, D. Raes, and M. Smith, Crop evapotranspiration -
Guidelines for computing crop water requirements, FAO Irrigation and drainage
paper no. 56, 1998.

AUTHOR AND COPYRIGHT
====================

``gerarda`` was written by Antonis Christofides, anthony@itia.ntua.gr.

| Copyright (C) 2014 TEI of Epirus

``gerarda`` is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

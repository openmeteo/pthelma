====
pond
====

------------------------------------------------------
Local filesystem cache of data from an Enhydris server
------------------------------------------------------

:Manual section: 1

SYNOPSIS
========

``pond [--traceback] config_file``

DESCRIPTION AND QUICK START
===========================

``pond`` downloads data from Enhydris and stores them locally in the
file system.  The details of its operation are specified in the
configuration file specified on the command line.

(The name ``pond`` comes from the fact that water snakes like Enhydris
normally live in lakes, but they can tempoorarily visit ponds.)

Installation
------------

To install ``pond``, see :ref:`install`.

How to run it
-------------

First, you need to create a configuration file with a text editor such
as ``vim``, ``emacs``, ``notepad``, or whatever. Create such a file
and name it, for example, :file:`/var/tmp/pond.conf`, or, on
Windows, something like :file:`C:\\Users\\user\\pond.conf` , with
the following contents (the contents don't matter at this stage, just
copy and paste them from below):

    [General]
    loglevel = INFO

Then, open a command prompt and give it this command:

**Unix/Linux**::

    pond /var/tmp/pond.conf

**Windows**::

    C:\Program Files\Pthelma\pond.exe C:\Users\user\pond.conf

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
    logfile = C:\Somewhere\pond.log
    cache_dir = C:\Somewhere\EnhydrisCache

    [ntua]
    base_url = https://openmeteo.org/
    id = 6539
    file = ntua.hts

    [nedontas]
    base_url = https://openmeteo.org/
    id = 9356
    file = C:\SomewhereElse\nedontas.hts

    [arta]
    base_url = https://upatras.gr/enhydris/
    user = george
    password = topsecret
    id = 8765
    file = arta.hts

With the above configuration file, ``pond`` will log information in
the file specified by :confval:`logfile`. It will download time series
from Enhydris and store them in the specified files; these can be
absolute or relative pathnames; if they are relative, they will be
stored in the directory specified by :confval:`cache_dir`. In this
example, the local files will be :file:`C:\\Somewhere\\ntua.hts`,
:file:`C:\\SomewhereElse\\nedontas.hts`, and
:file:`C:\\Somewhere\\arta.hts`.

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

.. confval:: cache_dir

   Optional. ``pond`` will change directory to this directory, so any
   relative filenames will be relative to this directory. If
   unspecified, relative filenames will be relative to the directory
   from which ``pond`` was started.

Time series sections
--------------------

The name of the section is ignored.

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

.. confval:: file

   The filename of the file to which the data will be cached. See also
   :confval:`cache_dir`.


AUTHOR AND COPYRIGHT
====================

``pond`` was written by Antonis Christofides,
anthony@itia.ntua.gr.

| Copyright (C) 2014 TEI of Epirus

``pond`` is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

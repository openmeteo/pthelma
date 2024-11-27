==========================================================
enhydris-cache - keep copies of time series in local files
==========================================================

Synopsis
========

``enhydris_cache [--traceback] config_file``

Description and quick start
===========================

``enhydris-cache`` downloads data from Enhydris and stores them
locally in the file system.  The details of its operation are
specified in the configuration file specified on the command line.

How to run it
-------------

First, you need to create a configuration file with a text editor such
as ``vim``, ``emacs``, ``notepad``, or whatever. Create such a file
and name it, for example, :file:`/var/tmp/enhydris_cache.conf`,
with the following contents (the contents don't matter at this stage,
just copy and paste them from below)::

    [General]
    loglevel = INFO

Then, open a command prompt and give it this command::

    enhydris-cache /var/tmp/enhydris_cache.conf

If you have done everything correctly, it should output an error message
complaining that something in its configuration file isn't right.

Configuration file example
--------------------------

Take a look at the following example configuration file and read the
explanatory comments that follow it:

.. code-block:: ini

    [General]
    loglevel = INFO
    logfile = /var/log/enhydris-cache/enhydris-cache.log
    cache_dir = /var/cache/enhydris-cache

    [ntua]
    base_url = https://openmeteo.org/
    station_id = 1334
    timeseries_group_id = 4321
    timeseries_id = 6539
    file = ntua.hts

    [nedontas]
    base_url = https://openmeteo.org/
    station_id = 1482
    timeseries_group_id = 1234
    timeseries_id = 9356
    file = /somewhere/else/nedontas.hts

    [arta]
    base_url = https://upatras.gr/enhydris/
    auth_token = 123456789abcdef0123456789abcdef012345678
    station_id = 27
    timeseries_group_id = 2727
    timeseries_id = 8765
    file = arta.hts

With the above configuration file, ``enhydris_cache`` will log
information in the file specified by :confval:`logfile`. It will
download time series from Enhydris and store them in the specified
files; these can be absolute or relative pathnames; if they are
relative, they will be stored in the directory specified by
:confval:`cache_dir`. In this example, the local files will be
:file:`/var/cache/enhydris-cache/ntua.hts`,
:file:`/somewhere/else/enhydris-cache/nedontas.hts`, and
:file:`/var/cache/enhydris-cache/arta.hts`.

Configuration file reference
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

   Optional. ``enhydris_cache`` will change directory to this
   directory, so any relative filenames will be relative to this
   directory. If unspecified, relative filenames will be relative to
   the directory from which ``enhydris_cache`` was started.

Time series sections
--------------------

The name of the section is ignored.

.. confval:: base_url

   The base URL of the Enhydris installation that hosts the time
   series.  Most often the :confval:`base_url` will be the same for
   all time series, but in the general case you might want to get data
   from many Enhydris installations.

.. confval:: station_id

   The id of the station.

.. confval:: timeseries_group_id

   The id of the time series group.

.. confval:: timeseries_id

   The id of the time series.

.. confval:: auth_token

   Optional.  Needed if that Enhydris installation needs login in
   order to provide access to the data. You can get a token at the
   ``/api/auth/login/`` URL of Enhydris, such as
   https://openmeteo.org/api/auth/login/.

.. confval:: file

   The filename of the file to which the data will be cached. See also
   :confval:`cache_dir`.

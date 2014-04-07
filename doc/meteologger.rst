.. _meteologger:

:mod:`meteologger` --- Meteorological logger utilities
======================================================

.. module:: meteologger
   :synopsis: Meteorological logger utilities.
.. moduleauthor:: Antonis Christofides <anthony@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

This module is about meteorological loggers. Loggers are specialized
computers to which sensors are connected, and loggers log the
measurements of the sensors. The measurements logged in the logger are
eventually transferred to a computer (e.g. by GSM modems, or through
the internet, or by going to the site with your laptop, connecting it
to the logger, and copying the data) and written to a file. The
:class:`Datafile` class provides functionality particularly for
inserting such data to the database.

Datafile objects
----------------

The Datafile class is an abstract base class that is meant to be
subclassed. It provides functionality that is common to all kinds of
data files. However, each make of logger, or even each type of
software used to unload data from a logger, provides a different kind
of data file. Therefore, Datafile subclasses are specialized, each to
a specific kind of file.

.. class:: Datafile(base_url, cookies, datafiledict[, logger=None])

   A Datafile instance should never be constructed; instead, a
   subclass should be constructed; however, the call for constructing
   any subclass has the same arguments: *base_url* is the location of
   the target Enhydris installation. *cookies* is the value returned
   from :func:`enhydris_api.login`.  *datafiledict* is a
   dictionary containing values for :attr:`filename` and
   :attr:`datafile_fields`, and optionally for
   :attr:`subset_identifiers`, :attr:`delimiter`,
   :attr:`decimal_separator` and :attr:`date_format`.  The *logger*
   argument has nothing to do with meteorological logger; it is a
   Logger_ object to which error, progress, and debugging information
   is written.

   .. _Logger: http://docs.python.org/library/logging.html

   :class:`Datafile` has the following attributes and methods:

   .. attribute:: filename

      The pathname to the data file.

   .. attribute:: nullstr

      A string representation of error values, treated as NaN (null
      value). e.g. -6999

   .. attribute:: datafile_fields 

      A comma-separated list of integers representing the ids of the
      time series to which the data file fields correspond; a zero
      indicates that the field is to be ignored. The first number
      corresponds to the first field after the date (and other fixed
      fields, such as the possible subset identifier; which are those
      fields depends on the data file format, that is, the specific
      :class:`Datafile` subclass) and should be the id of the
      corresponding time series, or zero if the field is dummy; the
      second number correspondes to the second field after the fixed
      fields, and so on.
     
   .. attribute:: nfields_to_ignore

      This is used only in the simple format; it’s an integer that
      represents a number of fields before the date and time that
      should be ignored. The default is zero. If, for example, the
      date and time are preceeded by a record id, set
      ``nfields_to_ignore=1`` to ignore the record id.

   .. attribute:: subset_identifiers
       
      This is used only on some :class:`Datafile` subclasses. Some
      file formats mix two or more sets of measurements in the same
      file; for example, there may be ten-minute and hourly
      measurements in the same file, and for every 6 lines with
      ten-minute measurements there may be an additional line with
      hourly measurements (not necessarily the same variables). Such
      files have one or more additional distinguishing fields in each
      line, which helps to distinguish which set it is. We call these
      fields, which depend on the specific data file format, the
      **subset identifiers**.

      :class:`Datafile` (in fact its subclass) processes only one set
      of lines each time, and *subset_identifiers* specifies which
      subset it is. *subset_identifiers* is a comma-separated list of
      identifiers, and will cause :class:`Datafile` (in fact its
      subclass) to ignore lines with different subset identifiers.

   .. attribute:: delimiter
   
   .. attribute:: decimal_separator
   
   .. attribute:: date_format

      Some file formats may be dependent on regional settings; these
      formats (i.e. these :class:`Datafile` subclasses) support
      :attr:`delimiter`, :attr:`decimal_separator`, and
      :attr:`date_format`. :attr:`date_format` is specified in the
      same way as for strftime_.

      .. _strftime: http://docs.python.org/lib/module-time.html#time.strftime

   .. method:: Datafile.update_database()

      For each time series specified in the :attr:`datafile_fields`,
      retrieve the end date for the time series from the database,
      scan the data file, determine which is the first record of the
      time series not already stored in the database, and append that
      record and all subsequent record for the database. This is done
      for all time series specified in :attr:`datafile_fields`.

      The changes are not committed; the caller must commit them.

   .. method:: raise_error(line, msg)

      This is only meant to be used internally, i.e. called by
      subclasses whenever an error is found in a data file. The method
      raises an exception. *line* and *msg* are strings used in the
      error message.

   :class:`Datafile` subclasses need to define the following methods:

   .. method:: subset_identifiers_match(line)

      Return :const:`True` if *line* matches the
      :attr:`subset_identifiers`. The base method always returns
      :const:`True`, and subclasses only need to redefine it if the
      file format has subsets.

   .. method:: extract_date(line)

      Parse *line* and extract and return the date and time as a
      datetime_ object.

      .. _datetime: http://docs.python.org/library/datetime.html#datetime-objects
      
   .. method:: extract_value_and_flags(line, seq)

      Extract the value and flags in sequence *seq* from *line*, and
      return it as a tuple.  :samp:`{seq}=1` is the first field after
      the fixed field, and so on (similar to :attr:`datafile_fields`).



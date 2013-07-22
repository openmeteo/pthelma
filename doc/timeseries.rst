.. _timeseries:

:mod:`timeseries` --- Time series operations
============================================

.. module:: timeseries
   :synopsis: Timeseries operations.
.. moduleauthor:: Antonis Christofides <anthony@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

This module provides the :class:`Timeseries` class, which
represents a time series, and the helper :class:`TimeStep` class,
which represents a time step.

Helper functions
----------------

.. function:: datetime_from_iso(isostring)

   Return a :class:`datetime` object created from a string in ISO 8601
   format.  In the current implementation it only converts strings of
   the form YYYY-MM-DD, optionally followed by THH:mm, where T is a
   literal T. Instead of T, a lower case t or a space can also be
   used.

.. function:: isoformat_nosecs(adatetime[, sep])

   Same as adatetime.isoformat, but without seconds.

.. function:: strip_trailing_zeros(s)

    If s is a string holding a number, return it after deleting extra
    unneeded zeros following the decimal point, and possibly the
    decimal point itself.

.. function:: read_timeseries_tail_from_db(db, id)

    Reads the last record of a time series with id from the database.
    Returns a list of two strings. The first string is the time stamp
    of the last record, the second string is the value.
    *db* is an object that has a :meth:`cursor` method that returns 
    a :pep:`249` Cursor Object. For example, *db* can be a :pep:`249` 
    Connection Object or a :data:`django.db.connection` object. 

TimeStep objects
----------------

A time series record has two time stamps: the nominal timestamp and the
actual timestamp. The one that is stored and displayed is the nominal
timestamp; the one that is meant is the actual timestamp. For example, in a
monthly time series, the nominal timestamp could be 2008-01-01 00:00,
meaning January 2008 and probably displayed by application software as
2008-01; but this could mean "the time period that begins at 2008-01-01
08:00 and ends at 2008-02-01 08:00". In that case, the actual timestamp
would be 2008-02-01 08:00, because we make the convention that actual
timestamps mark either a moment or the end of an interval.

.. class:: TimeStep([length_minutes=0][, length_months=0][, nominal_offset=None][, actual_offset=(0,0)][, interval_type=None])

   .. attribute:: TimeStep.length_minutes
   .. attribute:: TimeStep.length_months

      The number of minutes or months in the time step, for example, a
      daily time series has ``length_minutes=1440``, ``length_months=0``;
      an annual time series has ``length_minutes=0``,
      ``length_months=12``. One of the two must be zero. If both are
      zero, this means that the time series has no particular time
      step (it is irregular).
              
   .. attribute:: TimeStep.interval_type

      Tells if the value is the sum, average, maximum, minimum, or vector
      average of the variable over the interval. Can be
      ``IntervalType.SUM``, etc. If time series records are instant
      values rather than interval, this is 0 or None.

   .. attribute:: TimeStep.nominal_offset

      A pair of integers indicating the number of minutes and months that
      must be added to a round timestamp to get to the nominal timestamp.
      For example, if an hourly time series has timestamps that end in
      :13, such as 01:13, 02:13, etc., then its nominal offset is 13
      minutes, 0 months, i.e., ``(13, 0)``. Monthly time series normally
      have a nominal timestamp of ``(0, 0)``, the timestamps usually
      being of the form 2008-02-01 00:00, meaning "February 2008" and
      usually rendered by application software as 2008-02. Annual
      timestamps have a nominal timestamp which normally has 0 minutes,
      but may have nonzero months; for example, a common offset in Greece
      is 9 months, which means that an annual timestamp is of the form
      2008-10-01 00:00, normally rendered by application software as
      2008-2009, and denoting the hydrological year 2008-2009.

      nominal_offset may be None, meaning that the timestamps can be
      irregular.

   .. attribute:: TimeStep.actual_offset

      A pair of integers indicating the number of minutes and months that
      must be added to the nominal timestamp to get to the actual
      timestamp.  Note the difference from :attr:`nominal_offset`, which
      is the offset from the round timestamp; the :attr:`actual_offset`
      must be added to the nominal offset to find the actual offset from
      the round timestamp. Actual offset for small time steps, such as up
      to daily, is usually zero, except if the nominal timestamp is the
      beginning of an interval, in which case the actual offset is equal
      to the length of the time step, so that the actual timestamp is the
      end of the interval. For monthly and annual time steps, the
      :attr:`actual_offset` is usually 1 and 12 months respectively.  For
      a monthly time series, an :attr:`actual_offset` of (-475, 1) means
      that 2003-11-01 00:00 (normally rendered as 2003-11) denotes the
      interval 2003-10-31 18:05 to 2003-11-30 18:05.

   .. method:: TimeStep.up(timestamp)

      Return the first nominal timestamp that is equal or later than
      *timestamp*.

   .. method:: TimeStep.down(timestamp)

      Return the last nominal timestamp that is equal or earlier than
      *timestamp*.

   .. method:: TimeStep.next(timestamp)

      Return the next nominal timestamp.

   .. method:: TimeStep.previous(timestamp)

      Return the previous nominal timestamp.

   .. method:: TimeStep.actual_timestamp(timestamp)

      Return the actual timestamp that corresponds to the specified
      nominal timestamp.

   .. method:: TimeStep.containing_interval(timestamp)

      This function assumes that the timeseries is an interval, even if
      :attr:`interval_type` is ``None``.  It returns the nominal
      timestamp that denotes the interval that contains the specified
      moment.

   .. method:: TimeStep.interval_endpoints(nominal_timestamp)

      Return, as a tuple, the two actual timestamps of the interval that
      has the specified nominal timestamp.

Timeseries objects
------------------

A Timeseries class works like a dictionary.  If *t* is a Timeseries
object, *t[date]* is the value (may be ``float('nan')`` to denote a
missing value), and *t[date].flags* is a set of strings.  The
dictionary keys are either :class:`datetime.datetime` objects or ISO
8601 strings.  You may set a value like this::

   t[date] = number     # keeps flags as they were, if record existed
   t[date] = (number, flags)

Timeseries class depends on the custom library *ts_core*, written in
standard C language, which is used for memory and file storage operations 
of time series objects in order to improve for performance and for memory 
consumption. The use of the core library should not affect the developer
who can use Timeseries class like every Python dictionary object.
The only difference is that the dictionary object is always sorted
by date since with every add / insert operation new items are 
placed automatically in the right position to keep the dictionay
sorted. There is no need to call timeseries.keys().sort().
*ts_core* library is required, for installation see the bundled
text in the ts_core directory in the repository.

.. class:: Timeseries([id=0, time_step=None, unit='', title='', timezone='',
                variable='', precision=None, comment='',
                driver=Timeseries.SQLDRIVER_PSYCOPG2])

   Create a new :class:`Timeseries` object. The arguments set initial
   values for the attributes described below.
   
   .. attribute:: Timeseries.id

      The id of the time series in the database. This attribute is
      only used by :meth:`read_from_db` and :meth:`write_to_db`.  When
      these methods are called, *id* specifies the id of the time
      series.

   .. attribute:: Timeseries.driver

      The SQL driver used for some specific database operations such
      as blob field writing. It may have the values of
      Timeseries.SQLDRIVER_PSYCOPG2 for PostgreSQL or
      Timeseries.SQLDRIVER_NONE for non database applications.

   .. attribute:: Timeseries.SQLDRIVER_PSYCOPG2

      A class member used to specify the database driver for
      PostgreSQL access. This is the default driver for Timeseries
      objects.

   .. attribute:: Timeseries.SQLDRIVER_NONE

      A class member used to specify the database driver for
      non database application. Use this driver when you wish not to
      load a database driver such as psycopg2 in your application.

   .. attribute:: Timeseries.time_step

      A :class:`TimeStep` object describing the time step of the time
      series.

   .. attribute:: Timeseries.unit

   .. attribute:: Timeseries.title

   .. attribute:: Timeseries.timezone

   .. attribute:: Timeseries.variable

   .. attribute:: Timeseries.comment

      The above text attributes are informational and can hold
      anything at all; *comment*, in particular, may be multiline
      while the rest should not. They are set by :meth:`read_file` and
      used by :meth:`write_file`. Other than that, they are not used.

   .. attribute:: Timeseries.precision

      This integer attribute specifies the number of decimal digits to
      which the values are precise. It can also be zero or negative;
      if, for example, it is -2, values are precise to the hundred.

      The attribute is set by :meth:`read_file` and used by
      :meth:`write_file`. It is currently not used anywhere else
      within the class, but a user interface that displays values to
      the user might use it in order to determine how many decimal
      digits to display. It can be None, meaning unknown or unset.

   .. method:: Timeseries.read(fp)

      Read time series from the filelike object *fp*, which must be in
      :ref:`text format <textformat>`; preserve original contents
      (unless overwritten).

   .. method:: Timeseries.write(fp[, start][, end])

      Write time series to the filelike object *fp*, in :ref:`text
      format <textformat>`. If :class:`datetime.datetime` objects *start*
      and *end* are mentioned, only write that range.

      In accordance with the :ref:`text format specification
      <textformat>`, time series are written using the CR-LF sequence
      to terminate lines. In order to produce fully compliant files,
      care should be taken that *fp*, or any subsequent operations on
      *fp*, do not perform text translation; otherwise, it may result
      in lines being terminated with CR-CR-LF. If *fp* is a file, it
      should have been opened in binary mode.

  .. method:: Timeseries.write_plain_values(fp, [nullstr=''])

     Write plain values to a filelike object *fp*, in a csv like
     format but without the c of csv. Each line of the text file
     contains one value only representing the actual value of the nth
     step of the time series. No timestamp or flags are specified.
     Null values are represented with the *nullstr* sequence; default
     is an empty string causing empty lines for null value records.

   .. method:: Timeseries.read_file(fp)

      Read time series from the filelike object *fp*, which must be in
      :ref:`file format <fileformat>`; preserve original contents
      (unless overwritten).

   .. method:: Timeseries.write_file(fp)

      Write time series to the filelike object *fp*, in :ref:`file
      format <fileformat>`. If :class:`datetime.datetime` objects
      *start* and *end* are mentioned, only write that range.

      See also :meth:`write` for information on the handling of the
      line terminators.
      
   .. method:: Timeseries.read_from_db(db[, bottom_only=False])

      Read time series from a relational database. The original object
      contents are deleted. *db* is an object that has a
      :meth:`cursor` method that returns a :pep:`249` Cursor Object.
      For example, *db* can be a :pep:`249` Connection Object or a
      :data:`django.db.connection` object. If *bottom_only* is set to
      True, only the bottom part is returned.

   .. method:: Timeseries.blob_create(s):

      This method is for internal use by Timeseries.write_to_db
      method. Creates a BLOB instance (such as bytea in PostgreSQL)
      according to driver attribute of the Timeseries object, by
      encoding the stream object s.

   .. method:: Timeseries.write_to_db(db[, transaction=None, commit=True])

      Write time series to database, entirely overwriting any existing
      with the same id. Note that only the data are written, and not
      any metadata such as time step information.

      *db* is an object that has a :meth:`cursor` method that returns a
      :pep:`249` Cursor Object. For example, *db* can be a :pep:`249`
      Connection Object or a :data:`django.db.connection` object.

      This method also needs to be able to commit and rollback (unless
      *commit* is ``False``), and therefore it needs an object that
      has methods :meth:`commit()` and :meth:`rollback`. If
      *transaction* is None, it is assumed that *db* has these
      methods; otherwise, *transaction* is used.  If *db* is a
      :pep:`249` Connection Object, you can therefore leave
      *transaction* unspecified; but if *db* is, for example, a
      :data:`django.db.connection` object, then you should set
      *transaction* to :data:`django.db.transaction`.

      If *commit* is ``False``, then the time series are written to
      the database without being committed (in that case, you don't
      need to specify *transaction*).

      .. _Performing raw SQL queries: http://docs.djangoproject.com/en/dev/topics/db/sql/

   .. method:: Timeseries.append_to_db(db[, transaction=None, commit=True])
      
      Append the contained records to the time series stored in the
      database. The arguments are the same as those for
      :meth:`write_to_db`. All the records must have a timestamp later
      than that of any already existing records in the database;
      otherwise, :exc:`ValueError` is raised.

   .. method:: Timeseries.append(b)

      The same as :meth:`update`, except that it checks that all the
      records of *b* have timestamps later than ``Timeseries``; otherwise, 
      :exc:`ValueError` is raised.

   .. method:: Timeseries.bounding_dates()

      Return the start and end dates as a tuple of
      :class:`datetime.datetime` objects.

   .. method:: Timeseries.items([pos=None])

      Same as inherited but returns the items in order. In other
      words, it returns an ordered list of (date, value) tuples, where
      *date* is a datetime_ object and *value* is a float object that
      also has a *flags* attribute.
      By specifying a ``pos`` index, only the item with that index in
      return. ``pos`` should be between 0, ``len(ts)-1`` or else an
      IndexError is raised.

      .. _datetime: http://docs.python.org/lib/module-time.html#time.datetime

   .. method:: Timeseries.index(date[, downwards=False])

      Return the index in :meth:`~Timeseries.items()` that has the
      specified date, or, if no such item exists, and
      :samp:`*downwards*=False`, return the index of the item
      immediately after *date*; if an item with *date* does not exist,
      and :samp:`*downwards*=True`, return the index of the item
      immediately before *date*.

   .. method:: Timeseries.item(date[, downwards=False])

      Same as :meth:`~Timeseries.index()`, but instead of the index
      return the item. The item is returned as a (date, value) tuple,
      where *date* is a datetime_ object and *value* is a float object
      that also has a *flags* attribute.

   .. method:: Timeseries.min([start_date=None], [end_date=None])
               Timeseries.max([start_date=None], [end_date=None])
               Timeseries.average([start_date=None], [end_date=None])
               Timeseries.sum([start_date=None], [end_date=None])

      Return minimum, maximum, average, or sum of the time series. If
      *start_date* and/or *end_date* are specified, the result is the
      minimum, maximum or average value for the specified interval.

      If the value cannot be computed (e.g. because the time series
      does not have any not-null values in the specified interval),
      these functions return ``float("NaN")``, with the exception of
      :meth:`sum`, which returns zero.

   .. method:: Timeseries.aggregate(target_step[, missing_allowed=0.0][, missing_flag][, last_incomplete=False][, all_incomplete=False])

      Process the time series, produce two new time series, and return
      these new time series as a tuple.  The first of these series is the
      aggregated series; the second one is the number of missing values
      in each time step (more on this below). Both produced time series
      have a time step of *target_step*, which must be a
      :class:`TimeStep` object.  The *nominal_offset*, *actual_offset*,
      and *interval_type* attributes of *target_step* are taken into
      account during aggregation; so if, for example, *target_step* is
      one day with ``nominal_offset=(480,0)``, ``actual_offset=(0,0)``,
      and an *interval_type* of ``IntervalType.SUM``, then aggregation is
      performed so that, in the resulting time series, a record with
      timestamp 2008-01-17 08:00 contains the sum of the values of the
      source series from 2008-01-16 08:00 to 2008-01-17 08:00.

      If *target_step.interval_type* is ``IntervalType.VECTOR_AVERAGE``,
      then the source records are considered to be directions in degrees
      (as in a wind direction time series); each produced record is the
      direction in degrees of the sum of the unit vectors whose direction
      is specified by the source records.

      If *target_step.interval_type* is ``None``, corresponding to
      instantaneous values, then for each record of the destination
      series, a record from the source time series is selected if this
      has the same nominal step. If a record is not found, then the
      resulting record is set as NULL.

      If some of the source records corresponding to a destination record
      are missing, *missing_allowed* specifies what will be done. If the
      ratio of missing values to existing values in the source record is
      greater than *missing_allowed*, the resulting destination record is
      null; otherwise, the destination record is derived even though some
      records are missing.  In that case, the flag specified by
      *missing_flag* is raised in the destination record. The second time
      series returned in the return tuple contains, for each destination
      record, a record with the same date, containing the number of
      missing source values for that destination record.

      If *last_incomplete* set to True, then the last record
      of the destination time series, can be derived from an
      incomplete month, year etc. If *all_incomplete* is set to True,
      then all the destination records are from aggregation to the
      same point as the last incomplete record. This is usefull to
      find i.e. the rainfall up to the same day for the year, when
      that day is the last daily record to be aggregated.

Other functions
---------------

.. function:: identify_events(ts_list, start_threshold, ntimeseries_start_threshold, time_separator, [, end_threshold=None, ntimeseries_end_threshold=None, start_date=None, end_date=None, reverse=False])

      Find precipitation or extreme events in the :class:`Timeseries`
      sequence *ts_list*. An event is defined as a time interval at
      the start of which there is a value at least *start_threshold*
      in at least *ntimeseries_start_threshold* time series, at the
      end of which there is a value less than *end_threshold* in at
      least all but *ntimeseries_end_threshold* time series, and
      separated by at least *time_separator* from the nearest similar
      event. Only the interval between *start_date* and *end_date* is
      examined, and all time series should have the same time stamps
      within that interval. If *reverse* is :const:`True`, then the
      function finds events where the values become less than the
      thresholds instead of greater (e.g. cold events). Returns the
      events as a sequence of :samp:`({start_date}, {end_date})` pairs.
      *end_threshold* defaults to *start_threshold*, and
      *ntimeseries_end_threshold* defaults to
      *ntimeseries_start_threshold*. All dates are
      :class:`datetime.datetime` objects; *time_separator* is a
      :class:`datetime.timedelta` object.

Streaming formats for Timeseries objects
----------------------------------------

:class:`Timeseries` objects can load and save their records in plain
text files or in a database. There are three formats: the *text
format* is generic text format, without metadata; the *file format* is
like the text format, but additionally contains headers with metadata;
and the *database format* is for storing to the database. These three
formats are described below.

.. _textformat:

Text format
^^^^^^^^^^^

The text format for a time series is us-ascii, one line per record,
like this:

    2006-12-23 18:34,18.2,RANGE

The three fields are comma-separated and must always exist.  In the
date field, the time may be missing. The character that separates the
date from the time may be either a space, or a lower case ``t``, or a
capital ``T`` (:class:`Timeseries` objects produce text format using a
space as date separator, but can read text format that uses ``t`` or
``T``). The second field always uses a dot as the decimal separator
and may be empty.  The third field is usually empty but may contain a
list of space-separated flags. The line separator should be the CR-LF
sequence used in MS-DOS and Windows systems. Code that produces text
format should always use CR-LF to end lines, but code that reads text
format should be able to also read lines that end in LF only, as well
as CR-CR-LF (for reasons explained in :meth:`Timeseries.write`).

In order to improve performance in file writes, the maximum length
of each time series record line is limited by a number of 255
characters. With a fix date string of 16 characters, three commas,
a value string with a mean size of 10 characters, this is leaving
about 220 characters per line for flags. Assuming a mean size
of 10 characters for each flags, this leaves space for 20 flags
per record which is more than sufficient. An attempt to write more
than 255 characters, raise an exception and stops every file write.

Flags should be encoded in ASCI (7 bit) character set. In case of
characters with code>127, the string will have errors in encodings
and probably this will stop some file operations. Client software
should prevent the writing of non ASCI characters for flags.

.. _fileformat:

File format
^^^^^^^^^^^

The file format is like this::

    Version=2
    Title=My timeseries
    Unit=°C

    2006-12-23 18:34,18.2,RANGE
    2006-12-23 18:44,18.3,

In other words, the file format consists of a header that specifies
parameters in the form ``Parameter=Value``, followed by a blank line,
followed by the timeseries in text format. The same conventions for
line terminators apply here as for the text format. The encoding of
the header section is UTF-8. 

Client as well server software should recognize UTF-8 files with
or without UTF-8 BOM (Byte Order Mark) in the begining of file.
Writes may or may not include the BOM, according OS. (Usually
Windows software attaches the BOM at the beginning of the file).

If header is omited (not a Version=2 is included), then read_file
method will try to read the file as raw data file by trying to
parse dates, values, flags from the begining. If a Version=2 string
is included then the head is parsed as a meta section and a
blank line as separator between head and data is expected.

Parameter names are case insensitive.
There may be white space on either side of the equal sign, which is
ignored. Trailing white space on the line is also ignored. A second
equal sign is considered to be part of the value. The value cannot
contain a newline, but there is a way to have multi-lined parameters
explained in the Comment parameter below. All parameters except
Version are optional: either the value can be blank or the entire
``Parameter=Value`` can be missing; the only exception is the Comment
parameter.

The parameters available are:

**Version**
    This must have the value 2 and must be the first parameter in the
    file. It is the only mandatory parameter; all the other are
    optional.

**Unit**
    A symbol for the measurement unit, like ``°C`` or ``mm``.

**Count**
    The number of records in the time series. If present, it need not
    be exact; it can be an estimate. Its primary purpose is to enable
    progress indicators in software that takes time to read large
    time series files. In order to determine the actual number of
    records, the records need to be counted.

**Title**
    A title for the time series.

**Comment**
    A multiline comment for the time series. Multiline comments are
    stored by specifying multiple adjacent Comment parameters, like
    this::

        Comment=This timeseries is extremely important
        Comment=because the comment that describes it
        Comment=spans five lines.
        Comment=
        Comment=These five lines form two paragraphs.

    The Comment parameter is the only parameter where a blank value is
    significant and indicates an empty line, as can be seen in the
    example above.

**Timezone**
    The time zone of the timestamps, in the format :samp:`{XXX}
    (UTC{+HHmm})`, where *XXX* is a time zone name and *+HHmm* is the
    offset from UTC. Examples are ``EET (UTC+0200)`` and ``VST
    (UTC-0430)``.

**Time_step**

**Nominal_offset**

**Actual_offset**

    These three parameters specify the time step; each one is a pair
    of comma-separated integers, like this::

        Time_step=1440,0
        Nominal_offset=480,0
        Actual_offset=0,0

    The first number designates minutes and the second designates
    months. If nominal_offset is missing, it means that the time
    series records can have irregular timestamps. If time_step is
    present, actual_offset must also be present. If time_step is
    missing, it means that the time series is irregular.  For more
    information on these three parameters, refer to the
    :class:`Timeseries` documentation.

**Interval_type**

    Has one of the values ``sum``, ``average``, ``maximum``,
    ``minimum``, and ``vector_average``. If absent it means that the
    time series values are instantaneous, they do not refer to
    intervals. For more information on this parameter, refer to
    :class:`TimeStep`.

**Variable**
    
    A textual description of the variable, such as ``Temperature`` or
    ``Precipitation``.

**Precision**

    The precision of the time series values, in number of decimal
    digits after the decimal separator. It can be negative; for
    example, a precision of -2 indicates values accurate to the
    hundred, such as 100, 200, 300 etc.

.. _databaseformat:

Database format
^^^^^^^^^^^^^^^

The database format is an extension of the text format.  The time
series records are stored in a database table with three columns named
*top*, *middle* and *bottom*.  *top* and *bottom* are plain text (e.g.
PostgreSQL TEXT or Oracle TLOB), whereas *middle* is a binary data
field (e.g. PostgreSQL BYTEA or Oracle BLOB) that contains data
compressed with the LZ77 algorithm. The concatenation of *top*,
uncompressed *middle*, and *bottom*, is the entire time series in text
format. *top* is a non-nullable column, but may contain an empty
string; *middle* is nullable; and *bottom* is non-nullable.

.. admonition:: Note

    *middle* contains only the compressed data, and no header, checksum,
    or anything else. As a result, programs such as :program:`gzip` and
    :program:`pkzip` cannot read it; instead, free libraries may be
    used when implementing this functionality, such as Python's
    :mod:`zlib`, C's zlib, Perl's IO::Zlib, and Delphi's
    TCompressionStream and TDecompressionStream.

*top* stores the first few lines of the time series text format, up to
around 100. *bottom* stores the last few lines of the file, at least
one. *middle* stores all the rest.  *bottom* is non-nullable and may
not be empty; if a time series is empty, there must be no row in
database table. If it contains only a few records, they must all be
stored in *bottom*, the other two fields being empty. If it contains
more records, a few must be stored in *top*, another few in *bottom*,
and the rest in *middle*.  Appending a record to the timeseries is
usually accomplished by simply appending to *bottom*.

The details of the operation depend on the code that implements the
database format. The operation of this module is detailed below, and
you would normally not care about it unless you write another
implementation. In that case, you should follow a similar algorithm
when writing to the database, although there are only two requirements
that cannot be violated:

1. The concatenation of *top*, uncompressed *middle*, and *bottom*,
   must be the time series in text format.
2. Either the entire time series must be stored at *bottom*, or at
   least one record must be in *top* and one in *bottom*.

.. admonition:: Note

   Why use this seemingly paradoxical system? The reason is that, by
   storing each time series as essentially one compressed unit, rather
   than, e.g., in a (id, date, value, flags) database table, we can
   retrieve it many times faster. Storing time series in a relational
   manner would not make much sense, because they are inherently not
   relational. About 20 times less disk space is being used. In
   addition, large time series are uncompressed on the client, thus
   easing network and server load. Finally, if 'top' and 'bottom' are
   kept small, it is very fast to perform the frequently needed
   operations of retrieving the first and last records and appending a
   record.  All other operations must practically retrieve/update the
   entire time series, which experience has shown that it is what is
   done anyway.

The database table must be complemented with two database functions,
*timeseries_start_date* and *timeseries_end_date*, which accept a
single *id* argument and return the start or end date of the time
series. For example::

    hydrotest=> select timeseries_start_date(696), timeseries_end_date(696);
     timeseries_start_date | timeseries_end_date 
    -----------------------+---------------------
     1950-08-01 08:00:00   | 1997-03-31 08:00:00
    (1 row)


The algorithm used by this module for storing timeseries is as
follows: Let *MAX_ALL_BOTTOM* be the maximum number of records that a
time series may have if it is to be entirely stored in *bottom*;
*ROWS_IN_TOP_BOTTOM* the number of time series records in *top* and in
*bottom*; *MAX_BOTTOM* the maximum number of records allowed in
*bottom*; and *MAX_BOTTOM_NOISE* noise to be added or subtracted (more
on this below). At the time of this writing, these constants have the
values 40, 5, 100 and 10 respectively.

When a time series is to be entirely written to the database (i.e.
merely appending rows), it is written as follows:

* If it contains up to *MAX_ALL_BOTTOM* records, it is stored in
  *bottom*, with *top* and *middle* being empty.
* Otherwise, the top *ROWS_IN_TOP_BOTTOM* records are stored in *top*,
  the bottom *ROWS_IN_TOP_BOTTOM* records are stored in *bottom*, and
  the rest are stored in *middle*.

When appending to the database, the operation is as follows:

* First, a random number, uniformly distributed between
  -*MAX_BOTTOM_NOISE* and +*MAX_BOTTOM_NOISE*, is calculated and added
  to *MAX_BOTTOM*.
* If, after appending, *bottom* would not have more records than the
  calculated number, records are merely appended to *bottom*.
* Otherwise, the entire time series is read from *top*, *middle* and
  *bottom*, and is appended to. The existing *top*, *middle* and
  *bottom* are subsequently discarded and the time series is entirely
  written to the databse.

This is done in order to avoid *bottom* from growing too much. The
reason noise is being used is in order to avoid reaching circumstances
where 20 or so time series will be repacked altogether. For example,
consider a program that every 10 minutes appends data from an
automatic meteorological station with 20 sensors that measure 20
timeseries. With ``MAX_BOTTOM=100`` and ``ROWS_IN_TOP_BOTTOM=5``, it
is possible that every 95 updates all 20 time series would have to be
repacked, which can be a great load. But if we add a random ±10 to the
test, then once in a while one or two time series will be repacked.

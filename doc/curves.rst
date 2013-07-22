:mod:`curves` --- Interpolation Curves
=================================================

.. module:: curves
   :synopsis: Interpolation curves.
.. moduleauthor:: Stefanos Kozanis <S.Kozanis@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

This module provide classes and helper functions to define
interpolation curves and to interpolate values on such
curves.

Variables and exception classes
-------------------------------

.. data:: MINDATE

   Midnight of the 1st January of the :data:`datetime.MINYEAR` that is
   1/1/1 00:00. It is used as default start_date for 
   :class:`TransientCurve` objects.

.. data:: MAXDATE

   Midnight of the 31rd December of the :data:`datetime.MAXYEAR` that is
   31/12/9999 00:00. It is used as default end_date for
   :class:`TransientCurve` objects.

.. exception:: NoInterpolCurveError:

   The exception class for invalid interpolation in 
   :class:`TransientCurveList` objects denoting usually the 
   imposibility to find a valid :class:`TransientCurve` for a
   specified date.

Helper functions
----------------

.. function:: read_meta_line(fp)

   Read one line from a file format header and return a (name, value)
   tuple, where name is lowercased. Returns ('', '') if the next line is
   blank. Raises :exc:`ParsingError` if next line in ``fp`` is not a 
   valid header line. (source code Copied from pthelma, time series 
   class)

CurvePoint objects
------------------

Represents a point of a :class:`InterpolatingCurve`.
A point of a curve is defined by its two co-ordinates, which are named
:attr:`independent` and :attr:`dependent`, rather than X and Y, because
in stage-discharge curves the independent variable (stage) is plotted
vertically, and X and Y would be confusing.

.. class:: CurvePoint(independent, dependent)

   .. attribute:: CurvePoint.independent

      The independent variable of the point (usually the abscissa or X).

   .. attribute:: CurvePoint.dependent

      The dependent variable of the point (usually the ordinate or Y).

   .. method:: CurvePoint.__eq__(other)

      Equality test between two :class:`CurvePoint` instances (the
      ``self`` and the ``other``). :meth:`__eq__` is a special class
      method, so you don't have to call it. It is defined only
      to allow equality test like: ``point1==point2``. Two points are
      equal only and if only their coordinates differ less or equal
      than 0.001 that is ``|x1-x2|<=0.001 AND |y1-y2|<=0.001``.

   .. method:: CurvePoint.v([reverse=False])

      Return coordinates as a tupple of (``independent``, ``dependent``)
      values. If parameter ``reverse`` is set to ``True`` returns the 
      tuple in the reversed order.

InterpolatingCurve objects
--------------------------

Stores a curve representing the relationship between an independent and a
dependent variable.

Use :class:`InterpolatingCurve` to store curves for stage-discharge,
discharge-sediment discharge, reservoir stage-surface area, reservoir
stage-volume, and so on. :class:`InterpolatingCurve` has properties 
for storing these curves and methods for interpolating values in the
curves.

A curve is defined by a set of points, an offset point, and a boolean
specifying whether to interpolate with linear or with power functions.

Interpolating curve acts like Python lists. If a is an interpolating
curve, you can access curve points with a[0], a[1], .... To delete
a single point: del(a[1]). Slicing is valid. To delete all curve
points use del(a[:]). a[0]=point is valid only if point is a valid
:class:`CurvePoint` class object. The same for a[0:2] = [point1, point2].
len(a) is the total points count etc.

.. class:: InterpolatingCurve([logarithmic=False][, offset=CurvePoint(0,0)])

   .. attribute:: InterpolatingCurve.logarithmic

      Specifies whether the interpolation should be done with power function.
      Set :attr:`logarithmic` to ``True`` to specify that the interpolation 
      between points is to
      be done with power functions, and to ``False`` to specify linear
      interpolation. If :attr:`logarithmic` is ``True``, the curve's segments 
      appear as straight
      lines on log-log charts; otherwise, they appear as straight lines on
      linear charts.

   .. attribute:: InterpolatingCurve.offset

      Specifies the offsets for log curves. :attr:`offset` is a :class:`CurvePoint`
      object and it is used only if :attr:`logarithmic` is ``True``, and specifies 
      the points at which the curve crosses the zero axes. For example, 
      if X is the independent variable and Y is the dependent, then the 
      curve crosses the X axis at point (X0, 0), 
      where X0=``offset.independent``.

   .. method:: InterpolatingCurve.add(\*args)
    
      Add :class:`CurvePoint` objects to the list. If ``*args`` contains
      only one argument, this should be a :class:`CurvePoint` object. If
      ``*args`` contains two values, these should be the independent,
      dependent values, with this order. If ``*args`` number is not
      1 or 2 then a :exc:`TypeError` is raised.

   .. method:: InterpolatingCurve.index(value)

      Returns the list index number of a curve point with ``value``.
      ``value`` should be a :class:`CurvePoint` object or else a 
      :exc:`TypeError` is raised.

   .. method:: InterpolatingCurve.insert(i, value)

      Insert the ``value`` at (before) the ``i`` th position of the point list.
      value should be a :class:`CurvePoint` object or else a 
      :exc:`TypeError` is raised.
      
   .. method:: InterpolatingCurve.first()

      Retuns the first item of the curve points list. Equivalent with
      ``curve[0]``.

   .. method:: InterpolatingCurve.last()

      Returns the last item of the curve points list. Equivalent with
      ``curve[len(curve)-1]``.
 
   .. method:: InterpolatingCurve.value_over_curve(value[, reverse=False])

      Check if ``value`` is greater than the last independent value of
      the curve. If ``reverse`` is set to ``True``, dependent value is used
      instead of independent.

   .. method:: InterpolatingCurve.value_in_curve_range(value[, reverse=False]) 
      
      Check if ``value`` is between first and last curve point
      independent values. If ``reverse`` is set to ``True``, dependent
      value is used instead of independent.

   .. method:: InterpolatingCurve.read_line(line[, columns=(0,1)])

      Parse independent and dependent values from a string line.
      Values are separated by comma (,). Parsed values are added to
      the curve list by the :meth:`add` method. By default the two first
      columns are read. If you specify a two integer values tuple
      other than (0,1), then these columns are used to parse values.

   .. method:: InterpolatingCurve.read_fp(fp[, columns=(0,1)])

      Read points using the :meth:`read_line` method from a file-like
      object ``fp``. Parsing stops when *EOF* is reached or an empty line is
      read. :meth:`read_fp` does not clear the items list before reading.
   
   .. method:: InterpolatingCurve.interpolate(value[, reverse=False])

      Interpolates a value in the curve.

      Call :meth:`interpolate` to interpolate a value assumed as independent variable,
      in the curve and determine the corresponding value for the dependent
      variable. If the specified value lies outside the segments of the curve,
      extrapolation is performed.

      If :attr:`logarithmic` is ``True``, one of the points can be Offset. Although this is a
      valid, using it for interpolation would mean taking the logarithm of
      zero. Thus, the point is ignored; if the value must be interpolated in
      a segment having :attr:`offset` as one of its ends, it is, instead, extrapolated
      in an adjacent segment. The result should be mathematically correct.

      If :attr:`logarithmic` is ``True`` and ``value`` to be
      interpolated plus the ``offset`` is less or equal than zero
      (``offset+value<=0``), then a :data:`float("NaN")` is return.

      If ``reverse`` set to ``True``, a reverse interpolation is performed
      (see :meth:`reverseinterpolate`)

   .. method:: InterpolatingCurve.reverseinterpolate(value)

      ``reverseinterpolate(value)`` is equivalent with 
      ``interpolate(value, True)``.  Determines the value of the 
      independent variable given the value of the dependent variable.

      :meth:`reverseinterpolate` is the opposite of :meth:`interpolate`; 
      it interpolates a value for the dependent variable into the curve 
      and returns the corresponding value for the independent variable.

      :meth:`reverseinterpolate` will only work correctly if the curve 
      represents a reversible function, i.e., if one and only one value 
      of the independent variable corresponds to any given value of the 
      dependent variable. If this condition does not hold, the behavior 
      of :meth:`reverseinterpolate` will be undefined (it will probably 
      return one of the possible answers).

      The remarks in :meth:`interpolate` about extrapolation are also 
      true for :meth:`reverseinterpolate`.

TransientCurve objects
----------------------

Stores a :class:`InterpolatingCurve` with a period of validity.

:class:`TransientCurve` is a :class:`InterpolatingCurve` class with the 
additional properties start_date and end_date, which specify the period
of validity of this curve. :class:`TransientCurve` is useful for representing
stage-discharge curves.

.. class:: TransientCurve([logarithmic=False][, offset=CurvePoint(0,0)][, extension_line=False][, start_date=MINDATE][, end_date=MAXDATE])

   .. attribute:: TransientCurve.logarithmic

   .. attribute:: TransientCurve.offset

      Inherited properties from :class:`InterpolatingCurve` class. See
      the above class documentation for details.

   .. attribute:: TransientCurve.extension_line

      Specifies a curve as extension line, usefull for stage-discharge
      curves definition.

   .. attribute:: TransientCurve.start_date

      The starting date of the validity period for the curve. If no
      :attr:`start_date` specified then :data:`MINDATE` is considered.

   .. attribute:: TransientCurve.end_date

      The ending date of the validity period for the curve. If no
      :attr:`end_date` specified then :data:`MAXDATE` is considered.

   .. method:: TransientCurve.read_fp(fp[, columns=(0,1)])

      Read meta and data from the file-like object ``fp``. Meta and
      data sections are divided by a blank (empty) line. Meta section
      is formated in the ``name=value`` style. Available meta tags to
      be parsed are: ``start_date`` or ``startdate``, ``end_date`` or
      ``enddate``, ``logarithmic``, ``extension``, ``offset``, all are 
      case insensitive. Dates are formated according to ISO: 
      ``yyyy-mm-dd HH:MM``, ``offset`` is a floating point value and
      boolean values can be ``True`` (case insensitive) in order to be
      activated. After meta section, data are read by the inherited
      :meth:`InterpolatingCurve.read_fp` method.
      
TransientCurveList objects
--------------------------
      
Stores a set of curves.

:class:`TransientCurveList` stores a set of curves and provides interpolating
functions that interpolate a value to the chronologically appropriate
:class:`TransientCurve`. :class:`TransientCurveList` is mostly useful for sets of
stage-discharge curves.

:class:`TransientCurveList` acts exactly like a python list with items
of :class:`TransientCurve` objects. (See :class:`InterpolatingCurve`
documentation for usage on list methods).

.. class:: TransientCurveList()

   .. method:: TransientCurveList.addcurve(curve)

      Add the :class:`TransientCurve` `curve` into the curve list by
      appending it. `curve` should be a :class:`TransientCurve` or
      else a :exc:`TypeError` is raised.

   .. method:: TransientCurveList.add([logarithmic=False][, offset=CurvePoint(0,0)][, extension_line=False][, start_date=MINDATE][, end_date=MAXDATE])
      
      Creates a new :class:`TransientCurve`, then adds it to the curve
      list by calling :meth:`addcurve` method. See
      :class:`TransientCurve` for attributes description.

   .. method:: TransientCurveList.index(value)

      Returns the list index number of a curve point with value of
      value. value should be a :class:`TransientCurve` object or else a 
      :exc:`TypeError` is raised.

   .. method:: TransientCurveList.insert(i, value)

      Insert the value at (before) the ith position of the point list.
      value should be a :class:`TransientCurve` object or else a 
      :exc:`TypeError` is raised.
      
   .. method:: TransientCurveList.first()

      Retuns the first item of the curve points list. Equivalent with
      ``list[0]``.

   .. method:: TransientCurveList.last()

      Returns the last item of the curve points list. Equivalent with
      ``list[len(list)-1]``.
       
   .. method:: TransientCurveList.find(date[, extension_line=False])

      Returns the appropriate :class:`TransientCurve` curve for the
      specified date ``date`` searching in the list for non-extension
      lines. If ``extension_line`` is set to ``True``, then the searching is
      executed only on extension lines of the list.

   .. method:: TransientCurveList.has_extension_lines()

      Returns ``True`` if extension lines are included in the list.

   .. method:: TransientCurveList.interpolate(date, value)

      Interpolate value ``value`` by choosing an appropriate curve
      for ``date`` date from the list. 
      If value is less or equal than the last
      independent value for a normal curve, then the interpolation is
      done on the normal curve. If value is greater than that point
      then if no extension curves are defined, extrapolation is beeing
      performed. If extension curves exist, two cases are assessed:
      In the first case the value lies between the last point of the
      normal curve and the first point of the extension curve, an
      interpolation is performed between these two points. In the
      second case, the extension curve is used to do interpolation.

      Interpolation operations are performed with the help of the
      :meth:`InterpolatingCurve.interpolate` method.

   .. method::  TransientCurveList.interpolate_ts(timeseries)
      
      Interpolates the values of a :class:`timeseries.Timeseries`
      object. Both date and value of each timeseries record is beeing
      used in order to choose the appropriate curve and then applicate
      the interpolation algorithm on that curve. Null values give null
      values as well. The result is return by a new time series object
      holding the interpolated values. Calculations are performed with
      the :meth:`interpolate` method of the current Class.

   .. method::  TransientCurveList.read_fp(fp)

      Load curve list data by reading the file-like object ``fp``.
      A meta section is read then several curve data are read by
      :class:`TransientCurve` :meth:`TransientCurve.read_fp`. Curve
      data are separated from meta data by an empty (blank) line. The
      only meta data value parsed is ``count`` (case insensitive)
      holding the total number of :class:`TransientCurve` objects in
      the list. All other meta data is ignored. :meth:`read_fp` does 
      not clear the items list before reading.

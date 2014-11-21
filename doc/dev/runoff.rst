.. _runoff:

:mod:`runoff` --- Runoff calculations
==========================================================

.. module:: runoff
   :synopsis: Runoff calculations
.. moduleauthor:: Stavros Anastasiadis <anastasiadis.st00@gmail.com>
.. sectionauthor:: Stavros Anastasiadis <anastasiadis.st00@gmail.com>
.. |I_a| replace:: I\ :sub:`a`
.. |S_max| replace:: S\ :sub:`max`

.. class:: SCS(CN, precipitation)

   Calculates runoff based on runoff Curve Number (CN). The init parameters provide values
   for some of the attributes (see below). The heart of the class is
   the :meth:`calculate` method; see its documentation for
   the methodology used.

   .. attribute:: CN
   
      The curve number emprical parameter (range 30 to 100), provided at class initialization time. The runoff Curve Number is based on the area's hydrologic soil group, land use, treatment and hydrologic condition.

   .. attribute:: precipitation

      A :class:`~timeseries.Timeseries` object with a daily
      precipitation series; provided at class initialization time.

   .. method:: calculate(start_date, end_date, L_factor)

      The SCS Runoff Curve Number method is developed by the United States Department of Agriculture (USDA) Soil Conservation Service (SCS) and is a method of estimating rainfall excess from rainfall.

      The runoff equation is:

      * P >= |I_a|, Q = 0
      * P <  |I_a|, Q = (P - |I_a|)^2 / P - |I_a| - S

      where:

      * Q: runoff (mm)
      * P: :attr:`precipitation` (mm)
      * |S_max|: maxixum soil moisture retention after runoff begins
      * |I_a|: is the initial abstraction.

      The :attr:`CN` is related:

      |S_max| = (1000 / :attr:`CN`) - 10

      *L_factor* is initial abstration factor and is generally assumed from literature as 0.2. The method default *L_factor* value is also 0.2.

      The method returns runoff for *end_date* in millimeters (mm) (**Note**: if method is used in catchment analysis, the return method must mupltiplied by catchment area).







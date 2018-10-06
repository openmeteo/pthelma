.. _swb:

:mod:`swb` --- Calculation of soil water balance
==========================================================

.. module:: swb
   :synopsis: Calculation of soil water balance
.. moduleauthor:: Stavros Anastasiadis <anastasiadis.st00@gmail.com>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

.. |D_r1| replace:: D\ :sub:`r,1`
.. |D_ri| replace:: D\ :sub:`r,i`
.. |D_ri-1| replace:: D\ :sub:`r,i-1`
.. |P_i| replace:: P\ :sub:`i`
.. |RO_i| replace:: RO\ :sub:`i`
.. |IR_ni| replace:: IR\ :sub:`n,i`
.. |CR_i| replace:: CR\ :sub:`i`
.. |ET_ci| replace:: ET\ :sub:`c,i`
.. |DP_i| replace:: DP\ :sub:`i`
.. |K_s| replace:: K\ :sub:`s`

.. class:: SoilWaterBalance(fc, wp, rd, kc, peff, irrigation_efficiency, precipitation, evapotranspiration, a=0, b=0, , rd_factor=1000, draintime=None)

   Calculates soil water balance. The init parameters provide values
   for some of the attributes (see below).
   (:ref:`Malamos et al. (2015) <malamos1>`, :ref:`Malamos et al. (2016) <malamos2>`)

   .. attribute:: evapotranspiration

      A :class:`~timeseries.Timeseries` object with a daily
      evapotranspiration series; provided at class initialization
      time.

   .. attribute:: fc

      The field capacity, provided at class initialization time.

   .. attribute:: irrigation_efficiency

      Irrigation method efficiency factor, provided at class initialization.

   .. attribute:: kc

      The crop coefficient, provided at class initialization time.

   .. attribute:: peff

      The crop depletion fraction, i.e. RAW/TAW, provided at class
      initialization time.

   .. attribute:: precipitation

      A :class:`~timeseries.Timeseries` object with a daily
      precipitation series; provided at class initialization time.

   .. attribute:: raw

      The readily available water:

         raw = :attr:`p` * :attr:`taw`

   .. attribute:: rd

      The crop root depth, provided at class initialization time. It
      can be in any unit of length.  If it is in a different unit than
      water depth variables (such as evapotranspiration,
      precipitation, irrigation and depletion) :attr:`rd_factor` is
      used to convert it.

   .. attribute:: rd_factor

      If the root depth is in a different unit than
      the water depth variables (such as evapotranspiration,
      precipitation, irrigation and depletion) :attr:`rd_factor` is
      used to convert it.  If the root depth is in metres and the
      water depth variables are in mm, specify
      ``rd_factor=1000``. Provided at class initialization time.

   .. attribute:: a

      The :attr:`a` is coefficient of draintime function with default zero.

   .. attribute:: b

      The :attr:`b` is coefficient of draintime function with default zero.

   .. attribute:: draintime

      The draintime is the time required for the soil to remove excess water up
      to field capacity :attr:`Fc` in mm.

      If not provided, draintime use calculation formula based on attr:`a`,
      :attr:`b` and :attr:`rd` (m):

         draitime = (:attr:`a` * (:attr:`rd` * 100) ** :attr:`b`

      Returns draintime in days.

   .. attribute:: taw

      The total available water:

         taw = (:attr:`fc` - :attr:`wp`) * :attr:`rd` * :attr:`rd_factor`

   .. attribute:: wp

      The wilting point, provided at class initialization time.

   .. attribute:: wbm_report

      A list with the intermediate calculations made by
      :meth:`root_zone_depletion`. Before the first time the method is
      called, it is an empty list.

   .. method:: water_balance(theta_init, theta_init, irr_event_days, start_date, end_date, FC_IRT=1, Dr_historical=None, as_report=False)

      This method calculates irrigation water needs.

      The method returns irrigation water needs for *end_date* in
      millimeters (mm).

      :attr:`irr_event_days` is an empty list in no irrigation days or a list of
      tuples in the form [ (datatime, water_amount)]

      If :attr:`Dr_historical` is defined then its used in model initial values.

      If :attr:`as_report` is set as True, the method return model run as list
      of dictionary for each day.


References
----------

.. _fao56:

R. G. Allen, L. S. Pereira, D. Raes, and M. Smith, Crop evapotranspiration -
Guidelines for computing crop water requirements, FAO Irrigation and drainage
paper no. 56, 1998.

.. _malamos1:

Malamos, N., Tsirogiannis, I.L., Christofides, A., and Anastasiadis,S.,
IRMA_SYS: a web-based irrigation management tool for agricultural cultivations
and urban landscapes.
In: IrriMed 2015 – Modern technologies, strategies and tools for sustainable
irrigation management and governance in Mediterranean agriculture. Bari, Italy, 2015.

.. _malamos2:

Malamos, N., Tsirogiannis, I.L., and Christofides, A.,
Modelling irrigation management services: the IRMA_SYS case.
International Journal of Sustainable Agricultural Management and Informatics,
2 (1), 1–18, 2016.

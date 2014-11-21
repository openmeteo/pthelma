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

.. class:: SoilWaterBalance(fc, wp, rd, kc, p, precipitation, evapotranspiration, irrigation_efficiency, rd_factor=1)

   Calculates soil water balance. The init parameters provide values
   for some of the attributes (see below). The heart of the class is
   the :meth:`root_zone_depletion` method; see its documentation for
   the methodology used.

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

   .. attribute:: p
   
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

   .. attribute:: taw

      The total available water:

         taw = (:attr:`fc` - :attr:`wp`) * :attr:`rd`

   .. attribute:: wp
   
      The wilting point, provided at class initialization time.

   .. method:: root_zone_depletion(start_date, initial_soil_moisture, end_date)

      This method calculates, in a simplified way, the root zone
      depletion.  The basis for the calculation is this formula:

         |D_ri| = |D_ri-1| - (|P_i| - |RO_i|) - |IR_ni| - |CR_i| + |ET_ci| + |DP_i|

      where:
      
      * i is the current time period (i.e. the current day).
      * |D_ri| is the root zone depletion at the end of the previous time
        period.
      * |P_i| is the precipitation.
      * |RO_i| is the runoff.
      * |IR_ni| is the net irrigation depth.
      * |CR_i| is the capillary rise.
      * |ET_ci| is the crop evapotranspiration.
      * |DP_i| is the water loss through deep percolation.

      |RO_i|, |CR_i| and |DP_i| are ignored and considered zero. The
      equation therefore becomes:

         |D_ri| = |D_ri-1| - |P_i| - |IR_ni| + |ET_ci|

      |ET_ci| is calculated using crop coefficient approach by multiplying :attr:`evapotranspiration` by  crop coefficient :attr:`kc`.

      The essential simplifying assumption of this method is that each
      time we irrigate we reach field capacity (i.e. zero depletion).
      Therefore, at the last irrigation date we have i=1 and |D_r1|\
      =0. The equation then becomes:

         |D_ri| = |D_ri-1| - |P_i| + |ET_ci|

      (we do not use |IR_ni|, since, if we irrigated, according to our
      assumption, we would restart with i=1 and |D_r1|\ =0).

      The point i=1 is specified by *start_date*, which is a
      :class:`~datetime.datetime` object. The *initial_soil_moisture*
      will usually equal :attr:`fc` (this, according to the essential
      simplifying assumption, means that the crop was irrigated on
      *start_date*). However, if the crop has not been irrigated
      recently, *initial_soil_moisture* will be set to another value
      (such as a soil moisture measurement made at *start_date*).

      Soil moisture and depletion are related with this formula:

         moisture = fc - depletion / (rd * rd_factor)

      so, since the *initial_soil_moisture* is given, |D_r1| is also
      known.

      The method returns the root zone depletion for *end_date* in millimeters (mm).
      :attr:`precipitation` and :attr:`evaporation` must have non-null
      records for all days from the day following *start_date* to
      *end_date*.

   .. method:: irrigation_water_amount(start_date, initial_soil_moisture, end_date)

      This method calculates irrigation water needs based on :attr:`root_zone_depletion` and  :attr:`irrigation_efficiency` factor (i.e. drip, sprinkler).

      The method returns irrigation water needs for *end_date* in millimeters (mm).

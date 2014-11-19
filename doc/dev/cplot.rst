.. _cplot:

:mod:`cplot` --- Contour plots 
================================

.. module:: cplot
   :synopsis: Contour plots.
.. moduleauthor:: Stefanos Kozanis <S.Kozanis@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

This module provides helper functions for contour plotting
on a map background, when data points are provided with
coordinates (x,y), values and name. Depends on matplotlib,
numpy and PIL.

Helper functions
----------------

.. function:: plot_contours(filename, points, options)

   Create a contour plot image based on data *points*.
   *points* is a list object containing tupples of
   the form (x, y, v, name) where x,y the coordinates
   of each point, v a floating point value or any
   non-arithmetic value (such as None or NaN) if
   the value is unknown. name is a string containing
   the point name for labeling.
   *filename* is the full path (containing directory)
   of the image file that will be written.
   *options* is a dictionary like object holding
   several options for the contours creation process.
   Options are explained bellow:

   * *contours_font_size*, see matplotlib documentation.
   * *labels_format*, e.g. '%f', see matplotlib documentation.
   * *draw_contours*, True to draw contours.
   * *color_map*, e.g. 'winter_r', 'hsv', 'hot' etc,
     see matplotlib documentation.
   * *labels_font_size*, see matplotlib documentation.
   * *text_color*, e.g. 'black', see matplotlib documentation.
   * *contours_color*, e.g. 'red', see matplotlib documentation.
   * *draw_labels*, True to draw labels.
   * *markers_color*, e.g. 'green', see matplotlib documentation.
   * *markers_style*, '+', '*' etc. see matplotlib documentation.
   * *draw_markers*, True to draw markers.
   * *granularity*, the detail of the contour grid. Start from a
     value of 30 increasing for much detail. Over 100 maybe is
     useless. Do not drop under 5.
   * *chart_bounds_bl_x*, the bottom left abscissa of the map.
   * *chart_bounds_bl_y*, the bottom left ordinate of the map.
   * *chart_bounds_tr_x*, the top right abscissa of the map.
   * *chart_bounds_tr_y*, the top right ordinate of the map.
   * *chart_bounds_srid*, the referense system for the coordinates,
     use a conformal projection such as UTM or spherical mercator to have 
     identical scales on x and y, e.g. 2100 for GRRS-87.
   * *compose_background*, set to True to overlay contours on a
     map background. The composition is realized with the PIL module.
   * *background_image*, the filename (w/o directory) of the
     background for composition.
   * *mask_image*, an optional image containing mixing values as
     alpha values, when composition method is 'composite'. See
     PIL documentation.
   * *compose_method*, e.g. 'add', 'multiply', 'blend',
     'composite', see PIL documentation.
   * *swap_bg_fg*, Swap the bacground and foreground (contours)
     image order. It has effect on some methods such as
     'composite', 'blend', 'add', 'subtract'.
   * *compose_alpha*, the mixing ration between bg and fg, has
     mean only for 'blend' method. It is used also in 'add' and
     'subtract' as scale parameter.
   * *compose_offset*, an offset parameter for 'add' and
     'subtract method'.
   * *backgrounds_path*, the path of the directory holding bacground
     and mask images.
   * *chart_large_dimension*, an integer tha specifies the large
     dimension of the chart produced.
   * *boundary_distance_factor*, the default value is 1. It specifies
     the size of the virtual boundary. If width, height are the
     dimensions of the displayed area, then the virtual boundary has a
     size of (1+2*fac)*width, (1+2*fac)*height. Factor values should
     be altered with caution.
   * *boundary_value*, default value is 0. This is the value of the
     points on the virtual boundary. A value of 0 is ok for rainfall
     events.
   * *boundary_mode* is an integer value, default is 0. If set to zero
     (0) then the boundary value specified by the boundary_value
     parameter is a constant number. If set to one (1) then the
     boundary_value is a factor to the mean value of all data points.
     Then the factor*mean_value is set to all data points on the
     boundary.

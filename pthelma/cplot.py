#!/usr/bin/python
"""
cplot - contour plotting

Copyright (C) 2005-2011 National Technical University of Athens
Copyright (C) 2011 Antonis Christofides, Stefanos Kozanis

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm

def plot_contours(filename, points, options):
    from scipy.interpolate import Rbf
    import numpy as np
    a = points
    GRANULARITY=options['granularity']
    (x0, y0, x1, y1) = (options['chart_bounds_bl_x'], 
                        options['chart_bounds_bl_y'],
                        options['chart_bounds_tr_x'], 
                        options['chart_bounds_tr_y'])
    dx, dy = (x1-x0)/GRANULARITY, (y1-y0)/GRANULARITY
    width, height = x1-x0, y1-y0

    # If we just interpolate, then the contours can be bad. What we actually
    # need to do is to tell the interpolator that far away the rainfall becomes
    # zero. So we actually work on a grid that is larger (three times larger),
    # we define rainfall at the edges as zero, we interpolate in there and
    # calculate the contours, and we crop it so that only its middle part is
    # shown. We call this grid the "greater" grid, so we suffix variables with
    # "gr" when they refer to it.
    # New update (2011-05-30 by Stefanos). The distance of boundary
    # can be altered by a factor (default value is 1) as well as
    # boundary value (default should be 0). Boundary mode 0 is for a
    # constant value, 1 for a ratio of the mean value
    bfac = options.get('boundary_distance_factor', 1)
    bvalue = options.get('boundary_value', 0)
    if options.get('boundary_mode', 0)==1:
        mean, count = 0, 0
        for p in a:
            if p:
                mean+=p[2]
                count+=1
        if count>0:
            mean/= count
            bvalue*= mean
    bwidth, bheight = bfac*width, bfac*height
    xgr0, ygr0, xgr1, ygr1 = (x0-bwidth, y0-bheight, x1+bwidth, y1+bheight)
    a.append((xgr0, ygr0, bvalue, 'virtual'))
    a.append((xgr1, ygr0, bvalue, 'virtual'))
    a.append((xgr0, ygr1, bvalue, 'virtual'))
    a.append((xgr1, ygr1, bvalue, 'virtual'))
    a.append((xgr0+bwidth/2, ygr0, bvalue, 'virtual'))
    a.append((xgr0+bwidth/2, ygr1, bvalue, 'virtual'))
    a.append((xgr0, ygr0+bheight/2, bvalue, 'virtual'))
    a.append((xgr1, ygr0+bheight/2, bvalue, 'virtual'))

    # Now interpolate
    x = [i[0] for i in a]
    y = [i[1] for i in a]
    z = [i[2] for i in a]
    rbfi = Rbf(x, y, z, function='linear')
    xx = np.arange(xgr0, xgr1+dx, dx)
    yy = np.arange(ygr0, ygr1+dy, dy)
    zz = np.empty([3*GRANULARITY+1, 3*GRANULARITY+1])
    for i in xrange(0, 3*GRANULARITY):
        for j in xrange(0, 3*GRANULARITY):
            zz[j][i] = rbfi(xx[i], yy[j])
    # Crop
    zz = zz[GRANULARITY:2*GRANULARITY+1, GRANULARITY:2*GRANULARITY+1]

    # Create the chart
    chart_large_dimension = float(options['chart_large_dimension'])
    chart_small_dimension = chart_large_dimension*min(y1-y0, x1-x0)/max(
                                                                y1-y0, x1-x0)
    if x1-x0>y1-y0:
        x_dim, y_dim = chart_large_dimension, chart_small_dimension
    else:
        x_dim, y_dim = chart_small_dimension, chart_large_dimension
    x_dim, y_dim = round(x_dim), round(y_dim)
    fig = plt.figure(figsize=(x_dim/100.0, y_dim/100.0), dpi=100.0)
    ax = plt.axes([0.0, 0.0, 1.0, 1.0]) # Axes should occupy no space
    ax.set_xticks([])
    ax.set_yticks([])
    plt.axis('off')
    for x, y, z, name in a:
        if name=='virtual': continue
        if options['draw_markers']:
            plt.plot(x, y, marker=options['markers_style'], linestyle='None',
                     color=options['markers_color'])
        if options['draw_labels']:
            plt.text(x, y, name, color=options['text_color'],
                     fontsize=options['labels_font_size'])
    args = [zz,]
    kwargs = {'interpolation': 'bilinear', 'origin': 'lower',
        'extent': (x0, x1, y0, y1)}
    if options['color_map']!='': 
        kwargs['cmap']=getattr(cm, options['color_map']) 
    im = plt.imshow(*args, **kwargs)
    if options['draw_contours']:
        cs = plt.contour(zz, extent=(x0, x1, y0, y1),
                         colors=options['contours_color'])
    plt.clabel(cs, inline=1, fontsize=options['contours_font_size'], fmt=options['labels_format'])

    fig.savefig(filename)

    if options['compose_background']:
        from PIL import Image, ImageChops
        contours = Image.open(filename)
        contours = contours.convert("RGB")
        cmethod = options['compose_method']
        size = contours.size
        background = Image.open(os.path.join(options['backgrounds_path'], options['background_image'])).convert("RGB")
        background_size = background.size
        if size!=background_size:
            background = background.resize(size)
        if cmethod=='composite':
            mask = Image.open(os.path.join(options['backgrounds_path'], options['mask_image']))
            mask_size = mask.size
            if size!=mask_size:
                mask = mask.resize(size)
        args = [background, contours]
        if options['swap_bg_fg']:
            args.reverse()
        if cmethod in ('blend', 'add', 'subtract'):
            args.append(options['compose_alpha'])
        if cmethod in ('add', 'subtract'):
            args.append(options['compose_offset'])
        if cmethod=='composite':
            args.append(mask)
        contours = getattr(ImageChops, cmethod)(*args)
        contours.save(filename)

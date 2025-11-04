=========================================
textbisect - Binary search in a text file
=========================================

This module provides functionality to search inside sorted text
files.  The lines of the files need not be all of the same length. The
module contains the following functions:

.. function:: text_bisect_left(a, x, lo=0, hi=None, key=lambda x: x)
   
   Locates the insertion point for line ``x`` in seekable filelike
   object ``a`` consisting of a number of lines; ``x`` must be specified
   without a trailing newline. ``a`` must use ``\n`` as the newline
   character and must not perform any line endings translation (use
   ``open(..., newline='\n')``).  The parameters ``lo`` and ``hi``, if
   specified, must be absolute positions within object ``a``, and
   specify which part of ``a`` to search; the default is to search the
   entire ``a``. The character pointed to by ``hi`` (or the last
   character of the object, if ``hi`` is unspecified) must be a newline.
   ``key`` is a function that is used to compare each line of ``a`` with
   ``x``; line endings are removed from the lines of ``a`` before
   comparison. ``a`` must be sorted or the result will be undefined. If
   ``x`` compares equal to a line in ``a``, the returned insertion point
   is the beginning of that line. The initial position of ``a`` is
   discarded. The function returns the insertion point, which is an
   integer between ``lo`` and ``hi+1``, pointing to the beginning of a
   line; when it exits, ``a`` is positioned there.
   
.. function:: text_bisect_right(a, x, lo=0, hi=None, key=lambda x: x)

   The same as :func:`text_bisect_left`, except that if ``x`` compares
   equal to a line in ``a``, the returned insertion point is the
   beginning of the next line.

.. function:: text_bisect(a, x, lo=0, hi=None, key=lambda x: x)

   Same as :func:`text_bisect_right`.

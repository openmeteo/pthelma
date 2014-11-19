.. _enhydris_api:

:mod:`enhydris_api` --- Enhydris API client
===========================================

.. module:: enhydris_api
   :synopsis: Enhydris API client
.. moduleauthor:: Antonis Christofides <anthony@itia.ntua.gr>
.. sectionauthor:: Antonis Christofides <anthony@itia.ntua.gr>

This modules has some functionality to make it easier to use the
Enhydris API.

.. function:: login(base_url, username, password)

   Logins to Enhydris and returns a dictionary containing cookies. *username*
   can be a false value (:const:`None` or :const:`''`, for example), in which
   case an empty dictionary is returned.

   Example::

      import requests
      from pthelma import enhydris_api

      ...

      base_url = 'https://openmeteo.org/'
      session_cookies = enhydris_api.login(base_url, 'admin', 'topsecret')

      # The following is a logged on request
      r = requests.get('https://openmeteo.org/api/Station/1334/',
                       cookies=session_cookies)
      # But you would normally write it like this:
      mydict = enhydris_api.get_model(base_url, session_cookies,
                                      'Station', 1334)
      
      # If the request requires a CSRF token, a header must be added
      r = requests.post('https://openmeteo.org/api/Timeseries/1825/',
                        cookies=session_cookies,
                        headers={'Content-type': 'application/json',
                                 'X-CSRFToken': session_cookies['csrftoken']},
                        data=timeseries_json)
      ts_id = r.text
      # But normally you don't need to worry because you'd write it like this:
      ts_id = enhydris_api.post_model(base_url, session_cookies, Timeseries,
                                      timeseries_json)

.. function:: get_model(base_url, session_cookies, model, id)

   Returns json data for the model of type *model* (a string such as
   'Timeseries' or 'Station'), with the given *id*.

.. function:: post_model(base_url, session_cookies, model, data)

   Creates a new model of type *model* (a string such as 'Timeseries'
   or 'Station'), with its data given by dictionary *data*, and
   returns its id.

.. function:: delete_model(base_url, session_cookies, model, id)

   Deletes the specified model. See :func:`get_model` for the
   parameters.

.. function:: read_tsdata(base_url, session_cookies, ts)

   Retrieves the time series data into *ts*, which must be a
   :class:`~timeseries.Timeseries` object.

.. function:: post_tsdata(base_url, session_cookies, timeseries)

   Posts a time series to Enhydris "api/tsdata", appending the records
   to any already existing. *session_cookies* is the value returned
   from :func:`.login`; *timeseries* is a
   :class:`~timeseries.Timeseries` object that has :attr:`id` defined.

.. function:: get_ts_end_date(base_url, session_cookies, ts_id)

   Returns a :class:`~datetime.datetime` object which is the last
   timestamp of the time series. If the time series is empty, it
   returns a :class:`~datetime.datetime` object that corresponds to 1
   January 0001 00:00.

.. function:: urljoin(*args)

   This is a helper function intended to be used mostly internally. It
   concatenates its arguments separating them with slashes, but
   removes trailing slashes if this would result in double slashes;
   for example::

      >>> urljoin('http://openmeteo.org', 'path/')
      'http://openmeteo.org/path/'
      >>> urljoin('http://openmeteo.org/', 'path/')
      'http://openmeteo.org/path/'

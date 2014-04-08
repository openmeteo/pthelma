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

      session_cookies = enhydris_api.login('https://openmeteo.org/',
                                           'admin',
                                           'topsecret')
      
      # The following is a logged on request
      r = requests.get('https://openmeteo.org/api/Station/1334/',
                       cookies=session_cookies)
      
      # If the request requires a CSRF token, a header must be added
      r = requests.post('https://openmeteo.org/api/Timeseries/1825/',
                        cookies=session_cookies,
                        headers={'Content-type': 'application/json',
                                 'X-CSRFToken': session_cookies['csrftoken']},
                        data=timeseries_json)

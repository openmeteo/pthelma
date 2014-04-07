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

   Logins to Enhydris and returns a dictionary containing cookies. For
   example::

      import requests
      from pthelma import enhydris_api

      ...

      cookies = enhydris_api.login('https://openmeteo.org/',
                                   'admin',
                                   'topsecret')
      
      # The following is a logged on request
      r = requests.get('https://openmeteo.org/stations/d/1334/',
                       cookies=cookies)

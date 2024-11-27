====================================================
enhydris-api-client - Python client for Enhydris API
====================================================

Example
=======

::

    from enhydris_api_client import EnhydrisApiClient

    with EnhydrisApiClient("https://openmeteo.org", "my_auth_token") as api_client:
        # Get a dict with attrs of station with id=42
        station = api_client.get_model(Station, 42)

        # Create a new station
        api_client.post_model(Station, data={"name": "my station"})


Reference
=========

``from enhydris_api_client import EnhydrisApiClient``

.. class:: EnhydrisApiClient(base_url, token=None)

   Creates and returns an api client. It can also be used as a context
   manager, though this is not necessary. If not used as a context
   manager, you might get warnings about unclosed sockets.

   Not specifying ``token`` is deprecated. ``token`` will become
   mandatory in future versions.

   .. method:: get_token(self, username, password)

      (Deprecated.) Gets an API token from Enhydris and thereafter uses
      it in subsequent requests. The method will be removed in future
      versions.

   .. method:: get_station(self, id)
               post_station(self, data)
               put_station(self, station_id, data)
               patch_station(self, station_id, data)
               delete_station(self, station_id)

      Methods that create, retrieve, update or delete stations. The
      ``data`` argument (for those methods that receive one) is a
      dictionary.  :meth:`~EnhydrisApiClient.get_station` returns a
      dictionary with the data for the station.
      ``~EnhydrisApiClient.post_station`` returns the created station's
      id.

   .. method:: get_timeseries_group(self, station_id, timeseries_group_id)
               post_timeseries_group(self, station_id, timeseries_group_id, data)
               put_timeseries_group(self, station_id, timeseries_group_id, data)
               patch_timeseries_group(self, station_id, timeseries_group_id, data)
               delete_timeseries_group(self, station_id, timeseries_group_id)

      Methods that create, retrieve, update or delete time series
      groups.  Similar to the ones for station.

   .. method:: list_timeseries(self, station_id, timeseries_group_id)
               get_timeseries(self, station_id, timeseries_group_id, timeseries_id)
               post_timeseries(self, station_id, timeseries_group_id, data)
               delete_timeseries(self, station_id, timeseries_group_id, timeseries_id)

      Methods that create, retrieve or delete time series. Similar to
      the ones for station. :meth:`~EnhydrisApiClient.list_timeseries`
      returns a list of dictionaries.

   .. method:: read_tsdata(self, station_id, timeseries_group_id, timeseries_id, start_date=None, end_date=None, timezone=None)
              .post_tsdata(self, station_id, timeseries_group_id, timeseries_id, ts)
              .get_ts_end_date(self, station_id, timeseries_group_id, timeseries_id, timezone=None)

      Methods that retrieve or update time series data.

      :meth:`~EnhydrisApiClient.read_ts_data` retrieves the time series
      data into a htimeseries object that it returns. If ``start_date``
      and/or ``end_date`` (aware datetime objects) are specified, only
      the part of the time series between these dates is retrieved. The
      timestamps are returned in the specified time zone. If
      unspecified, then they are returned in the time zone specified by
      the station's display_timezone_.

      :meth:`~EnhydrisApiClient.post_tsdata` posts a time series to
      Enhydris, appending the records to any already existing.  ``ts``
      is a :class:`HTimeseries` object.

      :meth:`~EnhydrisApiClient.get_ts_end_date` returns a ``datetime``
      object which is the last timestamp of the time series. If the time
      series is empty it returns ``None``. The returned timestamp is
      always naive, but it is in the specified ``timezone`` (or the
      station's display_timezone_ if unspecified).

      .. _display_timezone: https://enhydris.readthedocs.io/en/latest/dev/database.html#enhydris.models.Gentity.display_timezone

import datetime as dt

import numpy as np
from osgeo import gdal, osr


def setup_test_raster(
    filename: str,
    value: np.ndarray[np.float64, np.dtype[np.float64]],
    timestamp: dt.datetime | dt.date | None = None,
    srid: int = 4326,
    unit: str | None = None,
):
    """Save value, which is an np array, to a GeoTIFF file."""
    nodata = 1e8
    value[np.isnan(value)] = nodata
    f = gdal.GetDriverByName("GTiff").Create(filename, 3, 3, 1, gdal.GDT_Float32)
    try:
        if timestamp:
            f.SetMetadataItem("TIMESTAMP", timestamp.isoformat())
        if unit:
            f.SetMetadataItem("UNIT", unit)
        if srid == 4326:
            f.SetGeoTransform((22.0, 0.01, 0, 38.0, 0, -0.01))
        elif srid == 2100:
            f.SetGeoTransform((320000, 1000, 0, 4210000, 0, -1000))
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(srid)
        if int(gdal.__version__.split(".")[0]) > 2:
            sr.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        f.SetProjection(sr.ExportToWkt())
        f.GetRasterBand(1).SetNoDataValue(nodata)
        f.GetRasterBand(1).WriteArray(value)
    finally:
        f = None

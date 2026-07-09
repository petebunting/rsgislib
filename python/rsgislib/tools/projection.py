#!/usr/bin/env python
"""
The tools.projection module contains some useful tools for working with projections.
"""
import math
from typing import List

import numpy
from osgeo import osr

import rsgislib


def get_epsg_code_from_wkt(wkt_str: str) -> int:
    """
    Using GDAL to return the EPSG code for inputted WKT string.

    :return: the EPSG code.

    """
    epsg_code = None
    try:
        spat_ref = osr.SpatialReference()
        spat_ref.ImportFromWkt(wkt_str)
        spat_ref.AutoIdentifyEPSG()
        epsg_code = spat_ref.GetAuthorityCode(None)
        epsg_code = int(epsg_code)
    except Exception:
        epsg_code = None
    return epsg_code


def get_wkt_from_epsg_code(epsg_code: int) -> str:
    """
    Using GDAL to return the WKT string for inputted EPSG Code.

    :param epsg_code: integer variable of the epsg code.

    :return: string with WKT representation of the projection.

    """
    wkt_str = None
    try:
        spat_ref = osr.SpatialReference()
        spat_ref.ImportFromEPSG(epsg_code)
        wkt_str = spat_ref.ExportToWkt()
    except Exception:
        wkt_str = None
    return wkt_str


def get_osr_prj_obj(epsg_code: int) -> osr.SpatialReference():
    """
    A function which returns an OSR SpatialReference object
    for a given EPSG code.

    :param epsg_code: An EPSG code for the projection. Must be an integer.
    :return: osr.SpatialReference object.

    """
    spat_ref = osr.SpatialReference()
    spat_ref.ImportFromEPSG(int(epsg_code))
    return spat_ref


def degrees_to_metres(
    latitude: float, lon_size: float, lat_size: float
) -> (float, float):
    """
    Convert pixel sizes or distances in degrees to metres.

    :param latitude: latitude
    :param lon_size: numpy array of x pixel sizes (degrees)
    :param lat_size: numpy array of y pixel sizes (degrees)
    :return: x_size (numpy array of x pixel sizes (m)),
             y_size (numpy array of y pixel sizes (m))

    .. code:: python

        from rsgislib import tools
        x_size, y_size = tools.degrees_to_metres(52,1.0,1.0)

    """

    # Set up parameters for ellipse
    # Semi-major and semi-minor for WGS-84 ellipse
    ellipse = [6378137.0, 6356752.314245]

    radlat = numpy.deg2rad(latitude)

    Rsq = (ellipse[0] * numpy.cos(radlat)) ** 2 + (ellipse[1] * numpy.sin(radlat)) ** 2
    Mlat = (ellipse[0] * ellipse[1]) ** 2 / (Rsq**1.5)
    Nlon = ellipse[0] ** 2 / numpy.sqrt(Rsq)
    x_size = numpy.pi / 180 * numpy.cos(radlat) * Nlon * lon_size
    y_size = numpy.pi / 180 * Mlat * lat_size

    return x_size, y_size


def metres_to_degrees(latitude: float, x_size: float, y_size: float) -> (float, float):
    """
    Convert pixel sizes or distances in metres to degrees.

    :param latitude: latitude
    :param x_size: numpy array of x pixel sizes (m)
    :param y_size: numpy array of y pixel sizes (m)
    :return: lon_size (numpy array of x pixel sizes (degrees)),
             lat_size (numpy array of y pixel sizes (degrees))

    .. code:: python

        from rsgislib import tools
        x_size, y_size = tools.metres_to_degrees(52, 1.0, 1.0)

    """

    # Set up parameters for ellipse
    # Semi-major and semi-minor for WGS-84 ellipse
    ellipse = [6378137.0, 6356752.314245]

    radlat = numpy.deg2rad(latitude)

    Rsq = (ellipse[0] * numpy.cos(radlat)) ** 2 + (ellipse[1] * numpy.sin(radlat)) ** 2
    Mlat = (ellipse[0] * ellipse[1]) ** 2 / (Rsq**1.5)
    Nlon = ellipse[0] ** 2 / numpy.sqrt(Rsq)
    lon_size = x_size / (numpy.pi / 180 * numpy.cos(radlat) * Nlon)
    lat_size = y_size / (numpy.pi / 180 * Mlat)

    return lon_size, lat_size


def get_deg_coord_as_str(lat: float, lon: float, n_chars: int = 4) -> str:
    """
    A function which produces a string representation of the coordinate
    provided in degrees.

    :param lat: the latitude in degrees
    :param lon: the longitude in degrees
    :param n_chars: the number of characters to be used for each number.
    :return: string representation of the coordinates.

    """
    import rsgislib.tools.utils

    east_west = "e"
    if lon < 0:
        east_west = "w"
    north_south = "n"
    if lat < 0:
        north_south = "s"

    lat_str = rsgislib.tools.utils.zero_pad_num_str(
        lat,
        str_len=n_chars,
        round_num=True,
        round_n_digts=1,
        integerise=True,
        absolute=True,
        gain=10,
    )
    lon_str = rsgislib.tools.utils.zero_pad_num_str(
        lon,
        str_len=n_chars,
        round_num=True,
        round_n_digts=1,
        integerise=True,
        absolute=True,
        gain=10,
    )

    pos = "{}{}{}{}".format(north_south, lat_str, east_west, lon_str)
    return pos


def great_circle_distance(
    wgs84_p1: List[float], wgs84_p2: List[float], earth_radius=6378137.0
) -> float:
    """
    A function which calculates the great circle distance between two points
    provided in degrees and projected with WGS84.

    :param wgs84_p1: A point provided as a list [lon (x), lat (y)]
    :param wgs84_p2: A point provided as a list [lon (x), lat (y)]
    :param earth_radius: the radius of the earth to use for the calculation.
                         The unit of this distance will define the unit of the
                         returned distance. The default is 6,378,137 metres
                         and therefore the the returned distance will also be
                         in metres. However, if 6378.137 km was passed then the
                         returned value will be in km.
    :return: the great circle distance between the two points.

    """

    if (wgs84_p1[1] < -90.0) or (wgs84_p1[1] > 90.0):
        raise rsgislib.RSGISPyException(
            "Point 1 latitude is not within valid range (-90 - 90)"
        )

    if (wgs84_p2[1] < -90.0) or (wgs84_p2[1] > 90.0):
        raise rsgislib.RSGISPyException(
            "Point 2 latitude is not within valid range (-90 - 90)"
        )

    if (wgs84_p1[0] < -180.0) or (wgs84_p1[0] > 180.0):
        raise rsgislib.RSGISPyException(
            "Point 1 longitude is not within valid range (-180 - 180)"
        )

    if (wgs84_p2[0] < -180.0) or (wgs84_p2[0] > 180.0):
        raise rsgislib.RSGISPyException(
            "Point 2 longitude is not within valid range (-180 - 180)"
        )

    wgs84_rads_p1 = (math.radians(wgs84_p1[0]), math.radians(wgs84_p1[1]))
    wgs84_rads_p2 = (math.radians(wgs84_p2[0]), math.radians(wgs84_p2[1]))

    if wgs84_rads_p1[0] > wgs84_rads_p2[0]:
        lon_abs_diff = wgs84_rads_p1[0] - wgs84_rads_p2[0]
    else:
        lon_abs_diff = wgs84_rads_p2[0] - wgs84_rads_p1[0]

    central_angle_radians = math.acos(
        math.sin(wgs84_rads_p1[1]) * math.sin(wgs84_rads_p2[1])
        + math.cos(wgs84_rads_p1[1])
        * math.cos(wgs84_rads_p2[1])
        * math.cos(lon_abs_diff)
    )
    gt_circle_dist = earth_radius * central_angle_radians

    return gt_circle_dist


def format_coord_to_dms(deg_coord, is_latitude=True):
    """
    A function which formats a coordinate (latitude or longitude) to DD°MM'SS"

    :param deg_coord: Coordinate in degrees (WGS84) to be formatted.
    :param is_latitude: if true then latitude if false the longitude.
    :return: formatted string with DD°MM'SS"
    """
    # Determine the cardinal direction hemisphere
    if is_latitude:
        direction = "N" if deg_coord >= 0 else "S"
    else:
        direction = "E" if deg_coord >= 0 else "W"

    abs_deg = abs(deg_coord)
    d = int(abs_deg)
    m = int((abs_deg - d) * 60)
    s = round((abs_deg - d - m / 60) * 3600, 2)

    # Handle rounding overflow (e.g., 59.999" -> 60" -> add 1 to minute)
    if s >= 60:
        s = 0.0
        m += 1
    if m >= 60:
        m = 0
        d += 1

    return f"{d}°{m:02d}'{s:05.2f}\"{direction}"

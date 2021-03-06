import math

__author__ = "huziy"
__date__ = "$13 juil. 2010 13:34:52$"

from math import atan2
from util.geo.GeoPoint import GeoPoint
import numpy as np

EARTH_RADIUS_METERS = 0.637122e7  # mean earth radius used in the CRCM5 model for area calculation


# longitude and latitude are in radians
def get_nvector(rad_lon, rad_lat):
    return [np.cos(rad_lat) * np.cos(rad_lon), np.cos(rad_lat) * np.sin(rad_lon), np.sin(rad_lat)]


# p1 and p2 are geopoint objects
def get_distance_in_meters(*arg):
    """
    arg = point1, point2
    arg = lon1, lat1, lon2, lat2
    """
    if len(arg) == 2:  # if we have 2 geopoints as an argument
        [p1, p2] = arg
        n1 = p1.get_nvector()
        n2 = p2.get_nvector()
    elif len(arg) == 4:  # if we have the coordinates of two points in degrees
        x = np.radians(arg)
        n1 = get_nvector(x[0], x[1])
        n2 = get_nvector(x[2], x[3])
    else:
        raise Exception("get_distance_in_meters should be 2 or 4 parameters.")
    return EARTH_RADIUS_METERS * get_angle_between_vectors(n1, n2)


def get_angle_between_vectors(n1, n2):
    dy = np.cross(n1, n2)
    dy = np.dot(dy, dy) ** 0.5
    dx = np.dot(n1, n2)
    return atan2(dy, dx)


def lon_lat_to_cartesian(lon, lat, R=EARTH_RADIUS_METERS):
    """
    calculates x,y,z coordinates of a point on a sphere with
    radius R = EARTH_RADIUS_METERS
    """
    lon_r = np.radians(lon)
    lat_r = np.radians(lat)

    x = R * np.cos(lat_r) * np.cos(lon_r)
    y = R * np.cos(lat_r) * np.sin(lon_r)
    z = R * np.sin(lat_r)
    return x, y, z


def cartesian_to_lon_lat(x):
    """
     x - vector with coordinates [x1, y1, z1]
     returns [lon, lat]
    """

    lon = np.arctan2(x[1], x[0])
    lon = np.degrees(lon)
    lat = np.arcsin(x[2] / (np.dot(x, x)) ** 0.5)
    lat = np.degrees(lat)
    return lon, lat


def geo_uv_to_cartesian_velocity(u_we, v_sn, lons_rad, lats_rad):
    """
    Convert the geographic wind components into the cartesian components in the system with a center in the middle of the Earth
    :param u_we:
    :param v_sn:
    :param lons_rad:
    :param lats_rad:
    :return:
    """
    vel_x = -u_we * np.sin(lons_rad) - v_sn * np.sin(lats_rad) * np.cos(lons_rad)
    vel_y = u_we * np.cos(lons_rad) - v_sn * np.sin(lats_rad) * np.sin(lons_rad)
    vel_z = v_sn * np.cos(lats_rad)
    return np.array([vel_x, vel_y, vel_z])




#nvectors.shape = (3, nx, ny)
def get_coefs_between(nvectors1, nvectors2):
    return np.array([1.0 / (get_angle_between_vectors(v1, v2) * EARTH_RADIUS_METERS ) ** 2.0 for v1, v2 in
                     zip(nvectors1, nvectors2)])


def test():
    p1 = GeoPoint(-86.67, 36.12)
    p2 = GeoPoint(-118.4, 33.94)

    from geopy import distance

    print(EARTH_RADIUS_METERS, distance.EARTH_RADIUS)
    distance.EARTH_RADIUS = EARTH_RADIUS_METERS / 1000.0
    print(distance.GreatCircleDistance((-86.67, 36.12)[::-1], (-118.4, 33.94)[::-1]).m)

    print(get_distance_in_meters(p1, p2))
    print(get_distance_in_meters(p1.longitude, p1.latitude, p2.longitude, p2.latitude))
    print('Theoretical distance: %f km' % 2887.26)


if __name__ == "__main__":
    test()
    print("Hello World")

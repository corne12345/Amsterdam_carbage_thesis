
import pandas as pd
import random
import copy
import geopandas as gpd
import shapely


def adress_in_service_area(x, y, polygon_list = None):
    """
    function to see whether a certain household is within the service area of rest.
    The 
    Input is x and y coordinates of a house and a list of polygons of service area.
    If polygon_list is not given, it is created within the function. This makes
    the function more dynamic, but providing polygon_list increases speed.
    Returns boolean
    """
    point = shapely.geometry.Point(float(x),float(y))
    for polygon in polygon_list:
        if polygon.contains(point):
            return True
    return False

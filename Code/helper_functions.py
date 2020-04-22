
import pandas as pd
import random
import copy
import geopandas as gpd
import shapely


def adress_in_service_area(x, y, polygon_list = None):
    """
    function to see whether a certain household is within the service area of rest.
    The test criterion is a shapefile containing all places in the city of
    Amsterdam
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


def calculate_weighted_distance(good_result):
    """
    Function to calculated the weighted average walking distance as part of the
    score function. It calculates the mean difference per fraction and employs
    the weights assigned to them to combine it into a single score.

    Input:
    df_containing distance from all households to its nearest container
    per fraction (known as good_result)

    Output:
    float representing weighted average distance
    """
    rest_mean = good_result['rest_afstand'].mean()
    papier_mean = good_result['papier_afstand'].mean()
    glas_mean = good_result['glas_afstand'].mean()
    plastic_mean = good_result['plastic_afstand'].mean()
    textiel_mean = good_result['textiel_afstand'].mean()
#     print(rest_mean, papier_mean, glas_mean, plastic_mean, textiel_mean)
    score = 0.35 * rest_mean + 0.25 * plastic_mean + 0.2 * papier_mean + 0.15 * glas_mean + 0.05 * textiel_mean
    return score


def calculate_penalties(good_result, aansluitingen):
    """
    This function calculates all the penalties associated with the candidate
    solution. It does this by calculating the number of times all constraints
    are violated and applies the weighing that is associated with all these
    violations

    Input:
    dataframe good_result containing per adress or adress poi the distance
    to the nearest container for all fractions.
    dataframe aansluitingen containing for all clusters the amount of containers
    per fraction, the amount of people using these containers and the percentage
    of occupancy compared to the norm

    Output:
    The sum of all different penalties as a single float
    """
    penalty1 = good_result[good_result['rest_afstand'] > 100]
    penalty1_sum = (penalty1['rest_afstand'].sum() - 100 * penalty1.shape[0])/good_result.shape[0] * 0.35
    penalty2 = good_result[good_result['plastic_afstand'] > 150]
    penalty2_sum = (penalty2['plastic_afstand'].sum() - 150 * penalty2.shape[0])/good_result.shape[0] * 0.25
    penalty3 = good_result[good_result['papier_afstand'] > 150]
    penalty3_sum = (penalty3['papier_afstand'].sum() - 150 * penalty3.shape[0])/good_result.shape[0] * 0.2
    penalty4 = good_result[good_result['glas_afstand'] > 150]
    penalty4_sum = (penalty4['glas_afstand'].sum() - 150 * penalty4.shape[0])/good_result.shape[0] * 0.15
    penalty5 = good_result[good_result['textiel_afstand'] > 300]
    penalty5_sum = (penalty5['textiel_afstand'].sum() - 300 * penalty5.shape[0])/good_result.shape[0] * 0.05

    penalty6 = aansluitingen[aansluitingen['rest_perc'] > 100]
    penalty6_sum = (penalty6['poi_rest'] - (penalty6['rest'] * 100)).sum()/ good_result.shape[0] * 0.35 * 1000
    penalty7 = aansluitingen[aansluitingen['plastic_perc'] > 100]
    penalty7_sum = (penalty7['poi_plastic'] - (penalty7['plastic'] * 200)).sum()/ good_result.shape[0] * 0.25 * 1000
    penalty8 = aansluitingen[aansluitingen['papier_perc'] > 100]
    penalty8_sum = (penalty8['poi_papier'] - (penalty8['papier'] * 200)).sum()/ good_result.shape[0] * 0.2 * 1000
    penalty9 = aansluitingen[aansluitingen['glas_perc'] > 100]
    penalty9_sum = (penalty9['poi_glas'] - (penalty9['glas'] * 200)).sum()/ good_result.shape[0] * 0.15 * 1000
    penalty10 = aansluitingen[aansluitingen['textiel_perc'] > 100]
    penalty10_sum = (penalty10['poi_textiel'] - (penalty10['textiel'] * 750)).sum()/ good_result.shape[0] * 0.05 * 1000

    total_penalties = sum([penalty1_sum, penalty2_sum, penalty3_sum, penalty4_sum, penalty5_sum,\
                           penalty6_sum, penalty7_sum, penalty8_sum, penalty9_sum, penalty10_sum])
    return total_penalties


def containers_per_cluster(cluster_list):
    """
    This function does a modified version of one-hot encoding. It takes as input
    a list with the amount of containers per fraction (as a column in the dataframe)
    and returns the amount of the containers per fraction in the cluster. This
    function is to be used as an 'apply' function on an dataframe
    Input:
    - list containing cluster info [Glas: 3, Rest: 5]
    Returns:
    - 6 integers (amount of containers per fraction and a total)
    """
    rest = 0
    plastic = 0
    papier = 0
    glas = 0
    textiel = 0
    try:
        for i in cluster_list:
            if i.startswith("Rest:"):
                rest = int((i.split(':')[1]))
            if i.startswith("Plastic:"):
                plastic = int((i.split(':')[1]))
            if i.startswith("Papier:"):
                papier = int((i.split(':')[1]))
            if i.startswith("Glas:"):
                glas = int((i.split(':')[1]))
            if i.startswith("Textiel:"):
                textiel = int(i.split(':')[1])
    except:
        pass
    return rest, plastic, papier, glas, textiel, sum([rest, plastic, papier, glas, textiel])

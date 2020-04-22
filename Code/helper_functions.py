
import pandas as pd
import random
import copy
import geopandas as gpd

import shapely
from shapely.geometry import Polygon, Point


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


def join_api_db(db_df, api_df):
    """
    This function join the dataframes on garbage clusters from the API and the
    Postgres DB together to form a dataframe that has all the necessary information
    regarding identification, but also on the configuration of that cluster.
    Input:
    - db_df: dataframe from the database. Needs 'type' column and coordinates
    - api_df: dataframe from the API. needs coordinates.
    Returns:
    - joined: joined dataframe with all information
    """
    db_clusters = db_df[db_df['type'] == 'afval_cluster']
    joined = db_clusters.set_index(['cluster_x', 'cluster_y']).join(api_df.set_index(['cluster_x', 'cluster_y']), how='outer').reset_index()

    df_clusters_open = joined[joined['s1_afv_rel_nodes_poi'].isna()].reset_index()
    db_clusters_open = joined[joined['aantal_per_fractie'].isna()].reset_index()

    joined_try_2 = fix_remaining_into_frame(db_clusters_open, df_clusters_open)
    joined = joined.append([joined_try_2], ignore_index=True)

    return joined.dropna()


def fix_remaining_options(i, db_clusters_open, df_clusters_open, margin=10):
    """
    Function tries to match unmatches cluster entries from the database with a
    suitable option not matched in the API. This is done by increasing the margins
    for coordinates. This can be done in increasing margins. This is a subfunction
    in fix_remaining_into_frame.
    Inputs:
    - i: index of options to test(from fix_remaining_into_frame)
    - db_clusters_open: clusters from database not matched in dataframe
    - df_clusters_open: clusters from API not matched in dataframe
    - margin: distance margin in meters to match on (default = 10)
    Returns:
    - aantal_per_fractie: dict-like information on amount of containers
    - volume_per_fractie: dict-like information on volume of fractions
    - street_name: street_name of the cluster
    """
    test_option = db_clusters_open.iloc[i]
    x = float(test_option['cluster_x'])
    y = float(test_option['cluster_y'])
    #     print(x,y)
    square = Polygon([(x-margin, y-margin), (x-margin, y+margin), (x+margin, y+margin), (x+margin, y-margin)])
    df_clusters_open['point'] = df_clusters_open.apply(lambda row: Point(row['cluster_x'], row['cluster_y']),axis=1)
    df_clusters_open['fit'] = df_clusters_open['point'].apply(lambda point: point.within(square))
    try:
        to_return = df_clusters[df_clusters['fit']].iloc[0]
        return to_return['aantal_per_fractie'], to_return['volume_per_fractie'], to_return['street_name']
    except:
        return None, None, None

def fix_remaining_into_frame(db_clusters_open, df_clusters_open, margin=10):
    """
    This function assembles all cluster information that is not joined between
    database and API. It tries this matching again by taking some margins in the
    coordinates, to hopefully get a match.
    Inputs:
    - db_clusters_open: dataframe of database results not matched
    - df_clusters_open: dataframe of API results not matched
    - margin: margin to scan for in meters (default = 10)
    Returns:
    - dataframe of matches clusters from database filled with additional information
    from API
    """
    apf_list = []
    vpf_list = []
    str_list = []

    for i in range(db_clusters_open.shape[0]):
        tmp = fix_remaining_options(i, db_clusters_open, df_clusters_open, margin=margin)
        apf_list.append(tmp[0])
        vpf_list.append(tmp[1])
        str_list.append(tmp[2])

    db_clusters_open['aantal_per_fractie'] = apf_list
    db_clusters_open['volume_per_fractie'] = vpf_list
    db_clusters_open['street_name'] = str_list
    return db_clusters_open

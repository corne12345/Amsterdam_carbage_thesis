"""
This document contains a set of functions needed to perform analyses.

The functions described here are all functions that perform analyses in some
way necessary to calculate the final score on configurations of garbage
containers. The loading of data functions and the algorithms themselves are in
the other provided .py docs.
"""

from shapely.geometry import Polygon, Point
from .loading_data import create_aansluitingen, get_db_afvalcluster_info, \
    get_distance_matrix, distance_matrix_with_counts, create_all_households, \
    load_api_data


def calculate_weighted_distance(good_result, use_count=False, w_rest=0.35,
                                w_plas=0.25, w_papi=0.2, w_glas=0.15,
                                w_text=0.05):
    """
    Calculate weighted distance of an input dataframe.

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
    score = w_rest * rest_mean + w_plas * plastic_mean + w_papi * papier_mean + \
        w_glas * glas_mean + w_text * textiel_mean
    return score


def calculate_penalties(good_result, aansluitingen, use_count=False,
                        w_rest=0.35, w_plas=0.25, w_papi=0.2, w_glas=0.15,
                        w_text=0.05, return_all=False):
    """
    Calculate the amount of penalties based on described policies.

    This function calculates all the penalties associated with the candidate
    solution. It does this by calculating the number of times all constraints
    are violated and applies the weighing that is associated with all these
    violations. D_... contain the maximum allowed walking distance to a
    container of the specified fraction. P_... show the maximum amount of
    households connected to a container of the fraction specified.

    Input:
    dataframe good_result containing per adress or adress poi the distance
    to the nearest container for all fractions.
    dataframe connections containing for all clusters the amount of containers
    per fraction, the amount of people using these containers and percentage
    of occupancy compared to the norm

    Output:
    The sum of all different penalties as a single float
    """
    D_REST = 100
    D_PPG = 150
    D_TEXT = 300
    MAX_PERC = 100
    P_REST = 100
    P_PPG = 200
    P_TEXT = 750
    NORMAL = 1000

    penalty1 = good_result[good_result['rest_afstand'] > D_REST]
    penalty2 = good_result[good_result['plastic_afstand'] > D_PPG]
    penalty3 = good_result[good_result['papier_afstand'] > D_PPG]
    penalty4 = good_result[good_result['glas_afstand'] > D_PPG]
    penalty5 = good_result[good_result['textiel_afstand'] > D_TEXT]
    penalty6 = aansluitingen[aansluitingen['rest_perc'] > MAX_PERC]
    penalty7 = aansluitingen[aansluitingen['plastic_perc'] > MAX_PERC]
    penalty8 = aansluitingen[aansluitingen['papier_perc'] > MAX_PERC]
    penalty9 = aansluitingen[aansluitingen['glas_perc'] > MAX_PERC]
    penalty10 = aansluitingen[aansluitingen['textiel_perc'] > MAX_PERC]

    if not use_count:
        penalty1_sum = (penalty1['rest_afstand'].sum() - D_REST * penalty1.shape[0]) / good_result.shape[0] * w_rest
        penalty2_sum = (penalty2['plastic_afstand'].sum() - D_PPG * penalty2.shape[0]) / good_result.shape[0] * w_plas
        penalty3_sum = (penalty3['papier_afstand'].sum() - D_PPG * penalty3.shape[0]) / good_result.shape[0] * w_papi
        penalty4_sum = (penalty4['glas_afstand'].sum() - D_PPG * penalty4.shape[0]) / good_result.shape[0] * w_glas
        penalty5_sum = (penalty5['textiel_afstand'].sum() - D_TEXT * penalty5.shape[0]) / good_result.shape[0] * w_text
        penalty6_sum = (penalty6['poi_rest'] - (penalty6['rest'] * P_REST)).sum() / good_result.shape[0] * w_rest * NORMAL
        penalty7_sum = (penalty7['poi_plastic'] - (penalty7['plastic'] * P_PPG)).sum() / good_result.shape[0] * w_plas * NORMAL
        penalty8_sum = (penalty8['poi_papier'] - (penalty8['papier'] * P_PPG)).sum() / good_result.shape[0] * w_papi * NORMAL
        penalty9_sum = (penalty9['poi_glas'] - (penalty9['glas'] * P_PPG)).sum() / good_result.shape[0] * w_glas * NORMAL
        penalty10_sum = (penalty10['poi_textiel'] - (penalty10['textiel'] * P_TEXT)).sum() / good_result.shape[0] * w_text * NORMAL

    else:
        penalty1_sum = (penalty1['rest_afstand'].sum() - D_REST * penalty1['count'].sum())/good_result['count'].sum() * w_rest
        penalty2_sum = (penalty2['plastic_afstand'].sum() - D_PPG * penalty2['count'].sum())/good_result['count'].sum() * w_plas
        penalty3_sum = (penalty3['papier_afstand'].sum() - D_PPG * penalty3['count'].sum())/good_result['count'].sum() * w_papi
        penalty4_sum = (penalty4['glas_afstand'].sum() - D_PPG * penalty4['count'].sum())/good_result['count'].sum() * w_glas
        penalty5_sum = (penalty5['textiel_afstand'].sum() - D_TEXT * penalty5['count'].sum())/good_result['count'].sum() * w_text
        penalty6_sum = (penalty6['poi_rest'] - (penalty6['rest'] * P_REST)).sum() / good_result['count'].sum() * w_rest * NORMAL
        penalty7_sum = (penalty7['poi_plastic'] - (penalty7['plastic'] * P_PPG)).sum() / good_result['count'].sum() * w_plas * NORMAL
        penalty8_sum = (penalty8['poi_papier'] - (penalty8['papier'] * P_PPG)).sum() / good_result['count'].sum() * w_papi * NORMAL
        penalty9_sum = (penalty9['poi_glas'] - (penalty9['glas'] * P_PPG)).sum() / good_result['count'].sum() * w_glas * NORMAL
        penalty10_sum = (penalty10['poi_textiel'] - (penalty10['textiel'] * P_TEXT)).sum() / good_result['count'].sum() * w_text * NORMAL

    total_penalties = sum([penalty1_sum, penalty2_sum, penalty3_sum,
                          penalty4_sum, penalty5_sum, penalty6_sum,
                          penalty7_sum, penalty8_sum, penalty9_sum,
                          penalty10_sum])
    if return_all:
        return penalty1_sum, penalty2_sum, penalty3_sum, penalty4_sum,
        penalty5_sum, penalty6_sum, penalty7_sum, penalty8_sum,
        penalty9_sum, penalty10_sum
    return total_penalties


def calculate_simple_penalties(good_result, aansluitingen):
    """
    Return simplified version of penalties.

    Simplified version of penalty function that gives total amount of
    penalties.
    """
    penalty1 = good_result[good_result['rest_afstand'] > 100].shape[0]
    penalty2 = good_result[good_result['plastic_afstand'] > 150].shape[0]
    penalty3 = good_result[good_result['papier_afstand'] > 150].shape[0]
    penalty4 = good_result[good_result['glas_afstand'] > 150].shape[0]
    penalty5 = good_result[good_result['textiel_afstand'] > 300].shape[0]

    temp = (aansluitingen['poi_rest'] - aansluitingen['rest'] * 100)
    penalty6 = temp[temp > 0].sum()
    temp = (aansluitingen['poi_plastic'] - aansluitingen['plastic'] * 200)
    penalty7 = temp[temp > 0].sum()
    temp = (aansluitingen['poi_papier'] - aansluitingen['papier'] * 200)
    penalty8 = temp[temp > 0].sum()
    temp = (aansluitingen['poi_glas'] - aansluitingen['glas'] * 200)
    penalty9 = temp[temp > 0].sum()
    temp = (aansluitingen['poi_textiel'] - aansluitingen['textiel'] * 750)
    penalty10 = temp[temp > 0].sum()

    print(penalty1, penalty2, penalty3, penalty4, penalty5, penalty6, penalty7,
          penalty8, penalty9, penalty10)
    return penalty1+penalty2+penalty3+penalty4+penalty5+penalty6+penalty7 + \
        penalty8+penalty9+penalty10


def containers_per_cluster(cluster_list):
    """
    Convert list of configuration into counted category columns.

    This function does a modified version of one-hot encoding. It takes as
    input a list with the amount of containers per fraction (as a column in the
    dataframe) and returns the amount of the containers per fraction in the
    cluster. This function is to be used as an 'apply' function on an dataframe
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
    return rest, plastic, papier, glas, textiel, sum([rest, plastic, papier,
                                                      glas, textiel])


def join_api_db(db_df, api_df):
    """
    Join API dataframe and DB dataframe based on exact coordinates match.

    This function join the dataframes on garbage clusters from the API and the
    Postgres DB together to form a dataframe that has all the necessary
    information regarding identification, but also on the configuration of that
    cluster.
    Input:
    - db_df: dataframe from the database. Needs 'type' column and coordinates
    - api_df: dataframe from the API. needs coordinates.
    Returns:
    - joined: joined dataframe with all information
    """
    db_clusters = db_df[db_df['type'] == 'afval_cluster']
    joined = db_clusters.set_index(['cluster_x', 'cluster_y'])\
        .join(api_df.set_index(['cluster_x', 'cluster_y']), how='outer')\
        .reset_index()
    joined = joined.dropna()

    df_clusters_open = joined[joined['s1_afv_rel_nodes_poi']
                              .isna()].reset_index()
    db_clusters_open = joined[joined['aantal_per_fractie']
                              .isna()].reset_index()

    joined_try_2 = fix_remaining_into_frame(db_clusters_open, df_clusters_open)
    joined = joined.append([joined_try_2], ignore_index=True)

    return joined.drop('index', axis=1)


def fix_remaining_options(i, db_clusters_open, df_clusters_open, margin=10):
    """
    Find individual matches between API and DB.

    Function tries to match unmatches cluster entries from the database with a
    suitable option not matched in the API. This is done by increasing the
    margins for coordinates. This can be done in increasing margins. This is a
    subfunction in fix_remaining_into_frame.
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
    square = Polygon([(x-margin, y-margin), (x-margin, y+margin),
                      (x+margin, y+margin), (x+margin, y-margin)])
    df_clusters_open['point'] = df_clusters_open\
        .apply(lambda row: Point(row['cluster_x'], row['cluster_y']), axis=1)
    df_clusters_open['fit'] = df_clusters_open['point']\
        .apply(lambda point: point.within(square))
    try:
        to_return = df_clusters_open[df_clusters_open['fit']].iloc[0]
        return to_return['aantal_per_fractie'], \
            to_return['volume_per_fractie'], to_return['street_name']
    except:
        return None, None, None


def fix_remaining_into_frame(db_clusters_open, df_clusters_open, margin=10):
    """
    Try alternative methods to match API and DB using proximity.

    This function assembles all cluster information that is not joined between
    database and API. It tries this matching again by taking some margins in
    the coordinates, to hopefully get a match.
    Inputs:
    - db_clusters_open: dataframe of database results not matched
    - df_clusters_open: dataframe of API results not matched
    - margin: margin to scan for in meters (default = 10)
    Returns:
    - dataframe of matches clusters from database filled with additional
    information from API
    """
    apf_list = []
    vpf_list = []
    str_list = []

    for i in range(db_clusters_open.shape[0]):
        tmp = fix_remaining_options(i, db_clusters_open, df_clusters_open,
                                    margin=margin)
        apf_list.append(tmp[0])
        vpf_list.append(tmp[1])
        str_list.append(tmp[2])

    db_clusters_open['aantal_per_fractie'] = apf_list
    db_clusters_open['volume_per_fractie'] = vpf_list
    db_clusters_open['street_name'] = str_list
    return db_clusters_open


def add_shortest_distances_to_all_households(all_households,
                                             cluster_distance_matrix,
                                             use_count=False):
    """
    Find per POI shortest distance to container of each fraction.

    Function that searches for shortest distance per household and per fraction
    and adds this information to the all_households dataframe
    """
    cluster_distance_matrix = cluster_distance_matrix.sort_values(by='afstand')

    if use_count:
        shortest_rest = cluster_distance_matrix[cluster_distance_matrix['rest'] > 0].\
            groupby('naar_s1_afv_nodes').first()[['count', 'van_s1_afv_nodes',
                                                  'afstand']].\
            rename(columns={'van_s1_afv_nodes': 'poi_rest',
                            'afstand': 'rest_afstand'})
    else:
        shortest_rest = cluster_distance_matrix[cluster_distance_matrix
                                                ['rest'] > 0] \
                .groupby('naar_s1_afv_nodes')\
                .first()[['van_s1_afv_nodes', 'afstand']]\
                .rename(columns={'van_s1_afv_nodes': 'poi_rest',
                                 'afstand': 'rest_afstand'})
    shortest_plastic = cluster_distance_matrix[cluster_distance_matrix
                                               ['plastic'] > 0].\
        groupby('naar_s1_afv_nodes').first()[['van_s1_afv_nodes', 'afstand']].\
        rename(columns={'van_s1_afv_nodes': 'poi_plastic',
                        'afstand': 'plastic_afstand'})
    shortest_papier = cluster_distance_matrix[cluster_distance_matrix
                                              ['papier'] > 0].\
        groupby('naar_s1_afv_nodes').first()[['van_s1_afv_nodes', 'afstand']].\
        rename(columns={'van_s1_afv_nodes': 'poi_papier',
                        'afstand': 'papier_afstand'})
    shortest_glas = cluster_distance_matrix[cluster_distance_matrix
                                            ['glas'] > 0].\
        groupby('naar_s1_afv_nodes').first()[['van_s1_afv_nodes', 'afstand']].\
        rename(columns={'van_s1_afv_nodes': 'poi_glas',
                        'afstand': 'glas_afstand'})
    shortest_textiel = cluster_distance_matrix[cluster_distance_matrix
                                               ['textiel'] > 0].\
        groupby('naar_s1_afv_nodes').first()[['van_s1_afv_nodes', 'afstand']].\
        rename(columns={'van_s1_afv_nodes': 'poi_textiel',
                        'afstand': 'textiel_afstand'})

    all_households = all_households.set_index('naar_s1_afv_nodes').\
        join([shortest_rest, shortest_plastic, shortest_papier,
              shortest_glas, shortest_textiel], how='left')
    return all_households


def initial_loading(save_intermediate=False):
    """
    Combine all initial loading steps in one function.

    This function is the consecutive call of a few functions. This is used to
    make an initial environment before the algorithms are applied. It returns
    the variables all_households, rel_poi_df, joined and df_afstandn2. These
    can be formed independent of the configuration of the containers. After
    that a choice needs to be made regarding algorithms.
    """
    use_count = bool(input("Do you want to use addresses instead "
                           + "of clusters?"))
    subsectie = str(input("What stadsdeel do you want to make as a subsection"
                          + "(optional parameter)?"))
    if subsectie not in ['T', 'M', 'N', 'A', 'K', 'E', 'F', 'B']:
        subsectie = None

    api_df = load_api_data(subsectie=subsectie)
    print('API data loaded')
    rel_poi_df = get_db_afvalcluster_info()
    print('DB relation POIs loaded')
    all_households = create_all_households(rel_poi_df, subsectie=subsectie)\
        .rename(columns={'s1_afv_nodes': 'naar_s1_afv_nodes'})
    print('Table all households created')
    if save_intermediate:
        all_households.to_csv('households_in_area.csv')
    joined = join_api_db(rel_poi_df, api_df)
    print('API and DB joined')
    joined['rest'], joined['plastic'], joined['papier'], joined['glas'], \
        joined['textiel'], joined['totaal'] = zip(*joined['aantal_per_fractie']
                                                  .apply(lambda x:
                                                  containers_per_cluster(x)))
    print('containers per cluster determined')
    if use_count:
        df_afstandn2 = distance_matrix_with_counts()
    else:
        df_afstandn2 = get_distance_matrix()
    print('distance matrix loaded')
    return all_households, rel_poi_df, joined, df_afstandn2


def analyze_candidate_solution(joined, all_households, rel_poi_df,
                               df_afstandn2, clean=True, use_count=False,
                               return_all=False):
    """
    Analyze the score and penalties of a provided solution.

    This function is the repeated calling of different functions. It is the
    third element of the data pipeline. The first step is initial_loading(),
    the second part is the proposed use of algorithms to modify the
    configuration of the garbage clusters and this part is a series of
    functions to use this modification to calculate the score associated with
    it. Returns not only score but also other dataframes for future use in the
    pipeline.
    """
    joined_cluster_distance = joined.set_index('s1_afv_nodes')\
        .join(df_afstandn2.set_index('van_s1_afv_nodes')).reset_index()\
        .rename(columns={'index': 'van_s1_afv_nodes'})

    good_result_rich = \
        add_shortest_distances_to_all_households(all_households,
                                                 joined_cluster_distance,
                                                 use_count)
    if clean:
        good_result_rich = good_result_rich[good_result_rich['uses_container']]

    aansluitingen = create_aansluitingen(good_result_rich,
                                         joined_cluster_distance,
                                         use_count=use_count)

    avg_distance = calculate_weighted_distance(good_result_rich,
                                               use_count=use_count)
    penalties = calculate_penalties(good_result_rich, aansluitingen,
                                    use_count=use_count, return_all=return_all)

    print("Average distance is : " + str(avg_distance))
    print("Penalties are: " + str(penalties))
    return joined_cluster_distance, good_result_rich, aansluitingen,\
        avg_distance, penalties

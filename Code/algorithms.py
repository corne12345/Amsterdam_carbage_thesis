import random
import copy
import pandas as pd

from helper_functions import *
from loading_data import *

def random_shuffling_clusters(cluster_join):
    """
    Function that makes a random shuffling. It takes as input a dataframe containing
    information on both the API data as well as the DB information (as for the POIs).
    Returns another configuration of the same information
    """
    df = cluster_join.set_index('s1_afv_nodes')[['rest', 'plastic', 'papier', 'glas', 'textiel', 'totaal']]
    df = df[df['totaal'] < 80]
    df = df.fillna(0)

    fractionlist = df['rest'].astype('int').sum() * ['rest'] + df['plastic']\
    .astype('int').sum() * ['plastic'] + df['papier'].astype('int').sum() * \
    ['papier'] + df['glas'].astype('int').sum() * ['glas'] + df['textiel'].\
    astype('int').sum() * ['textiel']
    random.shuffle(fractionlist)

    cluster_list = list()
    for i in df.index:
        cluster_list.extend([str(i)] * df.loc[i].totaal.astype('int'))

    df_new = pd.DataFrame([cluster_list, fractionlist]).T.rename(columns={0:'poi', 1:'fractie'})
    df_new['poi'] = df_new['poi'].astype('float').round(0).astype('int')
    df_new_apply = df_new.groupby('poi').fractie.value_counts().unstack()

    cluster_join1 = cluster_join.drop(['rest', 'plastic', 'papier', 'glas', 'textiel'], axis=1)
    cluster_join1['s1_afv_nodes'] = cluster_join1['s1_afv_nodes'].astype('int')

    cluster_join1 = cluster_join1.set_index('s1_afv_nodes')
    return cluster_join1.join(df_new_apply, how='left').reset_index()\
            .rename(columns={'index': 's1_afv_nodes'}).fillna(0)

def best_of_random(num_iterations, joined, all_households, rel_poi_df, df_afstandn2, clean=True, use_count=False):
    """
    Create multiple random candidate solutions and return the best one of these
    Num_iterations decides the amount of iterations. The best option is always
    returned and can also be the standard solution that is also included in this
    options. The best of random can subsequently used as input for some kind of
    iterative optimization process(hillclimber for example).
    """
    joined_cluster_distance, good_result_rich, aansluitingen, avg_distance, penalties = analyze_candidate_solution(joined, all_households, rel_poi_df, df_afstandn2, clean=clean, use_count=use_count)
    best = 0

    for i in range(num_iterations):
        joined2 = random_shuffling_clusters(joined)
        joined_cluster_distance2, good_result_rich2, aansluitingen2, avg_distance2, penalties2 = analyze_candidate_solution(joined2, all_households, rel_poi_df, df_afstandn2, clean=clean, use_count = use_count)
        if penalties2 < penalties:
            joined = joined2
            joined_cluster_distance = joined_cluster_distance2
            good_result_rich = good_result_rich2
            aansluitingen = aansluitingen2
            avg_distance = avg_distance2
            penalties = penalties2
            best = i

    print('***************************************')
    print(avg_distance, penalties, best)
    return joined_cluster_distance, good_result_rich, aansluitingen, avg_distance, penalties


def hillclimber(num_iterations, joined, all_households, rel_poi_df, df_afstandn2, mod_max = 5, parameter='score', complicated=True, clean=True, use_count=False, save=True):
    """
    Function to perform repeated hillclimber. This can be added as a building block
    directly to the standard solution, but also after for example a random algorithm.
    The results are to be seen.
    """
    joined_cluster_distance, good_result_rich, aansluitingen, avg_distance, penalties = analyze_candidate_solution(joined, all_households, rel_poi_df, df_afstandn2, clean=clean, use_count=use_count)

    if parameter == 'score':
        best = avg_distance + penalties
    if parameter == 'penalties':
        best = penalties

    hillclimber_dict = {}
    hillclimber_dict[0] = [avg_distance, penalties, best]

    r = copy.deepcopy(joined)
    for i in range(1, num_iterations+1):
        last = copy.deepcopy(r)
        fractions = ['rest', 'plastic', 'papier', 'glas', 'textiel']
        no_modifications = random.randint(1, mod_max)
#         print(no_modifications)
        for j in range(no_modifications):
            valid = False
            while not valid:
                location_a = random.randint(0, r.shape[0]-1)
                fraction_a = random.choice(fractions)
                location_b = random.randint(0, r.shape[0]-1)
                fraction_b = random.choice(fractions)

                if r.at[location_a, fraction_b] > 0 and r.at[location_b, fraction_a] > 0\
                                                    and fraction_a != fraction_b:
                    r.at[location_a, fraction_a] = int(r.at[location_a, fraction_a]) + 1
                    r.at[location_a, fraction_b] = int(r.at[location_a, fraction_b]) - 1
                    r.at[location_b, fraction_a] = int(r.at[location_a, fraction_b]) - 1
                    r.at[location_b, fraction_b] = int(r.at[location_a, fraction_b]) + 1
                    valid = True

        joined_cluster_distance2, good_result_rich2, aansluitingen2, avg_distance2, penalties2 = analyze_candidate_solution(r, all_households, rel_poi_df, df_afstandn2, clean=clean, use_count=use_count)
        hillclimber_dict[i] = [avg_distance2, penalties2, best, no_modifications]
        if parameter == 'score':
            print(avg_distance2+penalties2, best)
            if avg_distance2+penalties2 < best:
                best = avg_distance2+penalties2
            else:
                r = copy.deepcopy(last) # Undo modification
        if parameter == 'penalties':
            print(penalties2, best)
            if penalties2 < best:
                best = penalties2
            else:
                r = copy.deepcopy(last) # Undo modification

    hill_df = pd.DataFrame.from_dict(hillclimber_dict, orient='index')
    hill_df = hill_df.rename(columns={0:'avg_distance', 1:'penalties', 2:'best', 3:'amount of modifications'})

    if save:
        today = str(pd.datetime.now().date()) + '-' + str(pd.datetime.now().hour)
        hill_df.to_csv('hillclimber' + today + '.csv')
        r.to_csv('hillclimber_best_config' + today + '.csv')

    return hill_df, r

def random_start_hillclimber(joined, all_households, rel_poi_df, df_afstandn2):
    i = int(input("How many random iterations?"))
    j = int(input("How many iterations hillclimber?"))
    to_save = bool(input("Do you want the results saved(True/False)?"))
    clean = bool(input("Do you want to only use a subset of data?"))
    use_count = bool(input("Do you want to use addresses instead of clusters?"))
    parameter = str(input("What parameter to optimize on (score/penalties)?"))


    joined, joined_cluster_distance, good_result_rich, aansluitingen, \
        avg_distance, penalties = best_of_random(i, joined,all_households, \
        rel_poi_df, df_afstandn2, clean=clean, use_count=clean)

    hill_df, best_solution = hillclimber(j, joined, all_households, \
        rel_poi_df, df_afstandn2, clean=clean, use_count=use_count,\
        parameter=parameter, save=to_save)
    hill_df['best'].plot()
    return hill_df, best_solution

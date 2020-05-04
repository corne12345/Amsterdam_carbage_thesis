import random
import copy
import pandas as pd
import numpy as np
from collections import Counter

from .helper_functions import analyze_candidate_solution

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
    return joined, joined_cluster_distance, good_result_rich, aansluitingen, avg_distance, penalties


def hillclimber(num_iterations, joined, all_households, rel_poi_df, df_afstandn2, mod_max = 5, parameter='score', complicated=True, clean=True, use_count=False, save=True, prnt=False, method=False):
    """
    Function to perform repeated hillclimber. This can be added as a building block
    directly to the standard solution, but also after for example a random algorithm.
    The results are to be seen.
    """
    joined_cluster_distance, good_result_rich, aansluitingen, avg_distance, penalties = analyze_candidate_solution(joined, all_households, rel_poi_df, df_afstandn2, clean=clean, use_count=use_count)
    if method == False:
        method = input("2-opt or Gaussian as method?")

    if parameter == 'score':
        best = avg_distance + penalties
    if parameter == 'penalties':
        best = penalties

    hillclimber_dict = {}
    hillclimber_dict[0] = [avg_distance, penalties, best]

    r = copy.deepcopy(joined)
    for i in range(1, num_iterations+1):
        last = copy.deepcopy(r)

        if method == "2-opt":
            r, no_modifications = hillclimber_2_opt(r, mod_max, prnt=prnt)

        elif method == "Gaussian":
            r, no_modifications = hillclimber_variable_mutations(r)

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
    to_save = input("Do you want the results saved(True/False)?")
    if to_save == 'False':
        to_save = False
    clean = bool(input("Do you want to only use a subset of data?"))
    if clean == 'False':
        clean = False
    use_count = bool(input("Do you want to use addresses instead of clusters?"))
    if use_count == 'False':
        use_count = False
    parameter = str(input("What parameter to optimize on (score/penalties)?"))
    method = str(input("What method hillclimber(2-opt or Gaussian)?"))

    joined, joined_cluster_distance, good_result_rich, aansluitingen, \
        avg_distance, penalties = best_of_random(i, joined,all_households, \
        rel_poi_df, df_afstandn2, clean=clean, use_count=use_count)

    hill_df, best_solution = hillclimber(j, joined, all_households, \
        rel_poi_df, df_afstandn2, clean=clean, use_count=use_count,\
        parameter=parameter, save=to_save, method=method)
    plt = hill_df['best'].plot(title='hillclimber')
    return hill_df, best_solution


def hillclimber_2_opt(r, mod_max, prnt):
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

            if int(r.at[location_a, fraction_b]) > 0 and int(r.at[location_b, fraction_a]) > 0\
                                                and fraction_a != fraction_b:
                if prnt:
                    print(r.at[location_a, fraction_a], r.at[location_a, fraction_b], r.at[location_b, fraction_a], r.at[location_b, fraction_b])
                r.at[location_a, fraction_a] = int(r.at[location_a, fraction_a]) + 1
                r.at[location_a, fraction_b] = int(r.at[location_a, fraction_b]) - 1
                r.at[location_b, fraction_a] = int(r.at[location_b, fraction_a]) - 1
                r.at[location_b, fraction_b] = int(r.at[location_b, fraction_b]) + 1
                if prnt:
                    print(r.at[location_a, fraction_a], r.at[location_a, fraction_b], r.at[location_b, fraction_a], r.at[location_b, fraction_b])

                valid = True
    return r, no_modifications

def hillclimber_variable_mutations(df, x=1.9):

    df =df.fillna(0)
    df['p'] = np.random.normal(0, 1, size=df.shape[0])
    df_to_change = df[df['p'] > x]
    df = df[df['p'] < x]

    rest = df_to_change['rest'].sum() * ['rest']
    plastic = df_to_change['plastic'].sum() * ['plastic']
    papier = df_to_change['papier'].sum() * ['papier']
    glas = df_to_change['glas'].sum() * ['glas']
    textiel = df_to_change['textiel'].sum() * ['textiel']
    fracties = rest + plastic + papier + glas + textiel
    random.shuffle(fracties)

    df_to_change = df_to_change.drop(['rest', 'plastic', 'papier', 'glas', 'textiel'], axis=1)
    print("Amount of clusters to change: " + str(df_to_change.shape[0]))

    fractions_per_cluster = []
    start_point = 0
    for i in range(df_to_change.shape[0]):
        length = df_to_change['totaal'].iloc[i]
        fractions_per_cluster.append(fracties[start_point:start_point +length])
        start_point += length
    df_to_change['new_containers'] = fractions_per_cluster

    df_to_change['rest'], df_to_change['plastic'], df_to_change['papier'], df_to_change['glas'], df_to_change['textiel'] = zip(*df_to_change['new_containers'].apply(lambda x: count(x)))

    df = df.append(df_to_change, ignore_index=True)
    df = df.drop(['p', 'new_containers'], axis=1)
    return df, df_to_change.shape[0]


def count(lst):
    cnt = Counter()
    for word in lst:
        cnt[word] += 1
    return cnt['rest'], cnt['plastic'], cnt['papier'], cnt['glas'], cnt['textiel']

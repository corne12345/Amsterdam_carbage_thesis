"""Code for different algorithms and optimization techniques."""

import math
import random
import copy
import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime

from .helper_functions import analyze_candidate_solution, initial_loading
from .loading_data import create_all_households


def random_shuffling_clusters(cluster_join):
    """

    Transform cluster in a random order.

    It takes as input a dataframe
    containing information on both the API data as well as the DB information
    (as for the POIs). Returns another configuration of the same information.
    """
    cluster_join = cluster_join.drop_duplicates(subset='s1_afv_nodes')
    df = cluster_join.set_index('s1_afv_nodes')[['rest', 'plastic', 'papier',
                                                 'glas', 'textiel', 'totaal']]
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

    df_new = pd.DataFrame([cluster_list, fractionlist])\
        .T.rename(columns={0: 'poi', 1: 'fractie'})
    df_new['poi'] = df_new['poi'].astype('float').round(0).astype('int')
    df_new_apply = df_new.groupby('poi').fractie.value_counts().unstack()
    df_new_apply[['rest', 'plastic', 'papier', 'glas', 'textiel']] = \
        df_new_apply[['rest', 'plastic', 'papier', 'glas',
                      'textiel']].apply(pd.to_numeric, downcast='integer')

    cluster_join1 = cluster_join.drop(['rest', 'plastic', 'papier', 'glas',
                                       'textiel'], axis=1)
    cluster_join1['s1_afv_nodes'] = cluster_join1['s1_afv_nodes'].astype('int')

    cluster_join1 = cluster_join1.set_index('s1_afv_nodes')
    return cluster_join1.join(df_new_apply, how='left').reset_index()\
        .rename(columns={'index': 's1_afv_nodes'}).fillna(0)


def best_of_random(num_iterations, joined, all_households, rel_poi_df,
                   df_afstandn2, clean=True, use_count=False,
                   return_all=False):
    """
    Perform multiple random creations and save best result.

    Create multiple random candidate solutions and return the best one of these
    Num_iterations decides the amount of iterations. The best option is always
    returned and can also be the standard solution that is also included in the
    options. The best of random can subsequently used as input for some kind of
    iterative optimization process(hillclimber for example).
    """
    joined_cluster_distance, good_result_rich, aansluitingen, avg_distance, \
        penalties, simple_penalties = \
        analyze_candidate_solution(joined, all_households, rel_poi_df,
                                   df_afstandn2, clean=clean,
                                   use_count=use_count, return_all=return_all)
    best = 0

    for i in range(num_iterations):
        joined2 = random_shuffling_clusters(joined)
        joined_cluster_distance2, good_result_rich2, \
            aansluitingen2, avg_distance2, penalties2, simple_penalties2 = \
            analyze_candidate_solution(joined2, all_households, rel_poi_df,
                                       df_afstandn2, clean=clean,
                                       use_count=use_count,
                                       return_all=return_all)
        if penalties2 < penalties:
            joined = joined2
            joined_cluster_distance = joined_cluster_distance2
            good_result_rich = good_result_rich2
            aansluitingen = aansluitingen2
            avg_distance = avg_distance2
            penalties = penalties2
            simple_penalties = simple_penalties2
            best = i

    print('***************************************')
    print(avg_distance, penalties, best)
    return joined, joined_cluster_distance, good_result_rich, aansluitingen, \
        avg_distance, penalties, simple_penalties


def hillclimber(num_iterations, joined, all_households, rel_poi_df,
                df_afstandn2, mod_max=5, parameter='score', complicated=True,
                clean=True, use_count=False, save=True, method=False,
                start_x=1.3, x_gap=0.9, SA=False, return_all=False):
    """
    Perform repeated hillclimber to optimize candidate solution.

    Function to perform repeated hillclimber. This can be added as a building
    block directly to the standard solution, but also after for example a
    random algorithm. The results are to be seen.
    """
    joined_cluster_distance, good_result_rich, aansluitingen, avg_distance, \
        penalties, simple_penalties = \
        analyze_candidate_solution(joined, all_households, rel_poi_df,
                                   df_afstandn2, clean=clean,
                                   use_count=use_count, return_all=return_all)
    if not method:
        method = input("2-opt or Gaussian as method?")

    if parameter == 'score':
        best = avg_distance + penalties
    if parameter == 'penalties':
        best = penalties

    hillclimber_dict = {}
    hillclimber_dict[0] = [avg_distance, penalties, simple_penalties, best]

    r = copy.deepcopy(joined)
    for i in range(1, num_iterations+1):
        last = copy.deepcopy(r)

        if method == "2-opt":
            r, no_modifications = hillclimber_2_opt(r, mod_max)

        if method == "dim Gaussian":
            x = start_x + i * x_gap / num_iterations
            r, no_modifications = hillclimber_variable_mutations(r, x=x)

        elif method == "Gaussian":
            r, no_modifications = hillclimber_variable_mutations(r)

        joined_cluster_distance2, good_result_rich2,\
            aansluitingen2, avg_distance2, penalties2, simple_penalties2 = \
            analyze_candidate_solution(r, all_households, rel_poi_df,
                                       df_afstandn2, clean=clean,
                                       use_count=use_count,
                                       return_all=return_all)
        hillclimber_dict[i] = [avg_distance2, penalties2, simple_penalties2,
                               best, no_modifications]

        if parameter == 'score':
            print(avg_distance2+penalties2, best)
            if avg_distance2+penalties2 < best:
                best = avg_distance2+penalties2
            elif SA is True:
                if simulated_annealing(avg_distance2+penalties2,
                                       best, i) is True:
                    best = avg_distance2+penalties2
            else:
                r = copy.deepcopy(last)  # Undo modification
        if parameter == 'penalties':
            print(penalties2, best)
            if penalties2 < best:
                best = penalties2
            elif SA is True:
                if simulated_annealing(penalties2, best, i) is True:
                    best = penalties2
            else:
                r = copy.deepcopy(last)  # Undo modification

    hill_df = pd.DataFrame.from_dict(hillclimber_dict, orient='index')
    hill_df = hill_df.rename(columns={0: 'avg_distance', 1: 'penalties',
                                      2: 'simple_penalties', 3: 'best',
                                      4: 'amount of modifications'})

    if save:
        today = datetime.now().strftime("%Y%m%d-%H%M")
        hill_df.to_csv('hillclimber' + today + '.csv')
        r.to_csv('hillclimber_best_config' + today + '.csv')

    return hill_df, r


def random_start_hillclimber(joined, all_households, rel_poi_df, df_afstandn2,
                             i=100, j=5000, to_save=True, clean=True,
                             use_count=True, parameter='penalties',
                             method='Gaussian', prompt=True, SA=False):
    """
    Produce hillclimber optimization with a random optimal start.

    This function starts out with a random optimization, after which a kind of
    hillclimber optimization is performed. This optimized solution is then
    returned and a plot of the hillclimber is shown. This plot shows the amount
    of iteration on the x-axis and the score on the y-axis.
    """
    if prompt:
        i = int(input("How many random iterations?"))
        j = int(input("How many iterations hillclimber?"))
        to_save = input("Do you want the results saved(True/False)?")
        if to_save == 'False':
            to_save = False
        clean = input("Do you want to only use a subset of data?")
        if clean == 'False':
            clean = False
        else:
            clean = True
        use_count = input("Do you want to use addresses over clusters?")
        if use_count == 'False':
            use_count = False
        else:
            use_count = True
        SA = input("Do you want to apply simulated annealing? (True/False)")
        if SA == "False":
            SA = False
        else:
            SA = True
        parameter = str(input("Optimize on (score/penalties)?"))
        method = str(input("What method (2-opt, dim Gaussian, Gaussian)?"))

    joined, joined_cluster_distance, good_result_rich, aansluitingen, \
        avg_distance, penalties, simple_penalties = \
        best_of_random(i, joined, all_households, rel_poi_df, df_afstandn2,
                       clean=clean, use_count=use_count)

    hill_df, best = hillclimber(j, joined, all_households, rel_poi_df,
                                df_afstandn2, clean=clean, use_count=use_count,
                                parameter=parameter, save=to_save,
                                method=method, SA=SA)
    hill_df['best'].plot(title='hillclimber')
    return hill_df, best


def hillclimber_2_opt(r, mod_max):
    """
    Hillclimb using a 2-opt mutation strategy.

    The function takes as input a dataframe and the amount of 2-opt changes to
    be made before assessing validity. The function is looking for 2 containers
    that hold different fractions. If so, the containers will be swapped. This
    process is repeated unitl the mod_max is fulfilled. The modified dataframe
    is returned for further review.
    """
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

            if int(r.at[location_a, fraction_b]) > 0 and \
                    int(r.at[location_b, fraction_a]) > 0 and \
                    fraction_a != fraction_b and not (fraction_a == 'rest' and
                                                      ~r.at[location_a,
                                                            'move_rest']):
                r.at[location_a, fraction_a] = \
                    int(r.at[location_a, fraction_a]) + 1
                r.at[location_a, fraction_b] = \
                    int(r.at[location_a, fraction_b]) - 1
                r.at[location_b, fraction_a] = \
                    int(r.at[location_b, fraction_a]) - 1
                r.at[location_b, fraction_b] = \
                    int(r.at[location_b, fraction_b]) + 1

                valid = True
    return r, no_modifications


def hillclimber_variable_mutations(df, x=2.7):
    """
    Hillclimb with variable mutation strategy.

    This function uses Gaussian distribution to determine the amount of
    clusters to randomly re-assign. This can be modified by changing the
    optional parameter x. Its default setting of 1.9 allows for a small change.
    It returns a modified version of the input dataframe with some changes
    according to the specified x.
    """
    df = df.fillna(0)
    df['p'] = np.random.normal(0, 1, size=df.shape[0])
    df_to_change = df[df['p'] > x]
    if df_to_change.shape[0] < 2:  # Nothing happens in this case
        return df, df_to_change.shape[0]
    df = df[df['p'] < x]

    print("Amount of clusters to change: " + str(df_to_change.shape[0]))

    # Create upper threshold for grey area clusters
    df_to_change['rest_threshold'] = df_to_change['rest']
    df_to_change.loc[df_to_change['move_rest'], 'rest_threshold'] = 999

    # Extract all fractions
    rest = int(df_to_change['rest'].sum()) * ['rest']
    plastic = int(df_to_change['plastic'].sum()) * ['plastic']
    papier = int(df_to_change['papier'].sum()) * ['papier']
    glas = int(df_to_change['glas'].sum()) * ['glas']
    textiel = int(df_to_change['textiel'].sum()) * ['textiel']
    fracties = rest + plastic + papier + glas + textiel

    # lose the old configurations
    df_to_change = df_to_change.drop(['rest', 'plastic', 'papier',
                                      'glas', 'textiel'], axis=1)

    df_to_change = df_to_change.sort_values(by='rest_threshold')

    # Check if the new solution is valid. If not, repeat
    valid = False
    while not valid:
        fracties = plastic + papier + glas + textiel
        random.shuffle(fracties)
        fractions_per_cluster = []
        start_pnt = 0
        to_change = True
        for i in range(df_to_change.shape[0]):
            if df_to_change.iloc[i]['rest_threshold'] > 0 and to_change:
                to_change = False
                fracties = fracties + rest
                random.shuffle(fracties)
            length = df_to_change['totaal'].iloc[i]
            fractions_per_cluster.\
                append(fracties[start_pnt:start_pnt + length])
            start_pnt += length
        df_to_change['new_containers'] = fractions_per_cluster
        # print(df_to_change[['rest_threshold', 'new_containers']].head())

        df_to_change['rest'], df_to_change['plastic'], df_to_change['papier'], \
            df_to_change['glas'], df_to_change['textiel'] = \
            zip(*df_to_change['new_containers'].apply(lambda x: count(x)))
        if df_to_change[(df_to_change['rest'] > df_to_change['rest_threshold'])
                        & (df_to_change['rest_threshold'] < 999)]\
                .shape[0] == 0:

            valid = True

    df = df.append(df_to_change, ignore_index=True)
    df = df.drop(['p', 'new_containers'], axis=1)
    return df, df_to_change.shape[0]


def count(lst):
    """
    Count occurence of fractions in list.

    This function is part of an apply relation. It takese as input a list of
    different fractions. It returns the occurence of all these fractions based
    on a predefined format to be included as columns in a pandas dataframe.
    """
    cnt = Counter()
    for word in lst:
        cnt[word] += 1
    return cnt['rest'], cnt['plastic'], cnt['papier'], cnt['glas'], \
        cnt['textiel']


def clusterwise_optimization():
    """
    Perform clusterwise optimization without intermediate prompts.

    This function starts with loading in all data and then continues by
    performing optimization based on the input the user provides at the start
    of the function. This starts with performing subcluster analysis on the
    isolated stadsdelen in the city. This is followed by the remainder and
    all concluded by returning the best possible solution and showing graphs
    along the way and saving intermediate results.
    """
    import matplotlib.pyplot as plt
    i = int(input("How many random iterations?"))
    j = int(input("How many iterations hillclimber?"))
    to_save = input("Do you want the results saved(True/False)?")
    if to_save == 'False':
        to_save = False
    clean = bool(input("Do you want to only use a subset of data?"))
    if clean == 'False':
        clean = False
    use_count = bool(input("Do you want to use addresses over clusters?"))
    if use_count == 'False':
        use_count = False
    SA = input("Do you want to apply simulated annealing? (True/False)")
    if SA == "False":
        SA = False
    else:
        SA = True
    parameter = str(input("Optimize on (score/penalties/simple)?"))
    method = str(input("What method (2-opt, dim Gaussian, Gaussian)?"))

    all_households, rel_poi_df, joined, df_afstandn2 = initial_loading()

    print('Calculating starting point')
    joined_cluster_distance, good_result_rich, aansluitingen, avg_distance,\
        penalties, simple_penalties = \
        analyze_candidate_solution(joined, all_households, rel_poi_df,
                                   df_afstandn2, clean=clean,
                                   use_count=True)

    # Optimization of Zuidoost, Noord and Nieuw-West
    for k in ['T', 'N', 'F']:
        joined_T = joined[joined['stadsdeel'] == k]
        all_households_T = create_all_households(rel_poi_df, subsectie=k)
        all_households_T = all_households_T.\
            rename(columns={'s1_afv_nodes': 'naar_s1_afv_nodes'})
        hillclimber_df_T, best_solution_T = \
            random_start_hillclimber(joined_T, all_households_T, rel_poi_df,
                                     df_afstandn2, i=i, j=j, to_save=to_save,
                                     clean=clean, use_count=use_count,
                                     parameter=parameter, method=method,
                                     prompt=False, SA=SA)
        joined = joined[joined['stadsdeel'] != k]
        joined = joined.append(best_solution_T, ignore_index=True)
        print('**************************************************************')
        joined_cluster_distance, good_result_rich, aansluitingen, avg_distance,\
            penalties, simple_penalties = \
            analyze_candidate_solution(joined, all_households, rel_poi_df,
                                       df_afstandn2, clean=clean,
                                       use_count=True)
        print('**************************************************************')
        print(k + ' finished, moving on')
        plot = hillclimber_df_T['best'].plot(title='hillclimber of ' + k)
        plot.set_xlabel('Number of iterations')
        plot.set_ylabel('Penalty score')
        plot.figure.savefig('20200505_' + k + '.pdf')
        plt.close(plot.figure)

    # Optimization of Centrum
    # joined_C = joined[joined['stadsdeel'] == 'T']
    joined_C = joined[joined['stadsdeel'].isin(['M', 'A', 'K', 'E'])]
    # joined_C = joined_C.dropna()
    all_households_C = create_all_households(rel_poi_df,
                                             subsectie=['M', 'A', 'K', 'E'])
    # all_households_C = create_all_households(rel_poi_df,
    #                                          subsectie=['T'])
    all_households_C = all_households_C\
        .rename(columns={'s1_afv_nodes': 'naar_s1_afv_nodes'})
    hillclimber_df_C, best_solution_C = \
        random_start_hillclimber(joined_C, all_households_C, rel_poi_df,
                                 df_afstandn2, i=i, j=j, to_save=to_save,
                                 clean=clean, use_count=use_count,
                                 parameter=parameter, method=method,
                                 prompt=False, SA=SA)
    joined = joined[joined['stadsdeel'].isin(['T', 'N', 'F'])]
    joined = joined.append(best_solution_C, ignore_index=True)
    joined_cluster_distance, good_result_rich, aansluitingen, avg_distance, \
        penalties, simple_penalties = \
        analyze_candidate_solution(joined, all_households, rel_poi_df,
                                   df_afstandn2, clean=True, use_count=True)

    plt = hillclimber_df_T['best'].plot(title='hillclimber of ' + k)
    plt.set_xlabel('Number of iterations')
    plt.set_ylabel('Penalty score')
    plt.figure.savefig('20200505_' + 'C' + '.pdf')
    joined.to_csv('total_best_config.csv')

    return joined


def simulated_annealing(score_new, score_old, i, t0=5, alpha=0.999):
    """
    Perform simulated annealing to see if worsened solution is still accepted.

    This is a helper function of the already existing hillclimber function. It
    is only called in the case a candidate solution is worse than the initial
    solution. It checks with a predefined cooling schema whether or not this
    solution can still be accepted or not. The goal of simulated annealing is
    to allow for a more explorative character of an hillclimber. This hopefully
    prevents getting stuck in local optima.
    The default cooling schema is exponential and allows for worsening almost
    exclusively in the first iterations.
    """
    t = t0 * alpha ** i
    x = np.random.rand()
    p = math.exp((score_new-score_old)/t)
    if p > x:
        return True
    else:
        return False

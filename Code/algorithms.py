import random
import pandas as pd 

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

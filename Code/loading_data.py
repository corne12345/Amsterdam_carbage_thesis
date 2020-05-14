"""Functions to assist in loading of data."""

import geopandas as gpd
from sqlalchemy import create_engine
import pandas as pd
import requests
import shapely
import os

# Connect to Postgres database
# source: https://blog.panoply.io/connecting-jupyter-notebook-with-postgresql-
# for-python-data-analysis

# Postgres username, password, and database name
POSTGRES_ADDRESS = '10.243.25.5'
POSTGRES_PORT = '5432'
POSTGRES_USERNAME = 'heijne029'
# POSTGRES_PASSWORD = getpass(prompt='Password: ')
POSTGRES_PASSWORD = input("POSTGRES password?")
POSTGRES_DBNAME = 'analyse_ruimte'

# A long string that contains the necessary Postgres login information
postgres_str = ('postgresql://{username}:{password}@{ipaddress}:{port}/{db}'
                .format(username=POSTGRES_USERNAME,
                        password=POSTGRES_PASSWORD,
                        ipaddress=POSTGRES_ADDRESS,
                        port=POSTGRES_PORT,
                        db=POSTGRES_DBNAME))


def load_geodata_containers(subsectie=None):
    """
    Load shapefile concerning types of garbage collection.

    This function loads in all polygons representing areas in the city where
    general waste needs to be brought to a container. This is different from
    the alternative where general waste is collected from the sidewalk. This
    is needed to filter the address POI's to relevant POI's for optimization.
    Subsectie is optional parameter to filter on specific stadsdelen. This can
    be used for partial optimization.

    Returns:
    - List of polygons making up the area of centralized garbage collection
    """
    if os.path.isfile("data/shp/Inzameling_huisvuil_080520.shp"):
        source = gpd.read_file('data/shp/Inzameling_huisvuil_080520.shp')
    elif os.path.isfile("../data/shp/Inzameling_huisvuil_080520.shp"):
        source = gpd.read_file('../data/shp/Inzameling_huisvuil_080520.shp')
    source = source[source['aanbiedwij'] ==
                    'Breng uw restafval  naar een container voor restafval.']
    if subsectie:
        source = source[source['sdcode'].isin(list(subsectie))]
    return list(source.geometry)


def load_shapefile_neighborhood(area):
    """
    Return a shapefile consisting of the specified neighborhood.

    Function takes as input a certain specified area and return the shapefile
    that encloses this neighborhood.
    """
    if os.path.isfile("data/shp/Inzameling_huisvuil_080520.shp"):
        source = gpd.read_file('data/shp/Inzameling_huisvuil_080520.shp')
    elif os.path.isfile("../data/shp/Inzameling_huisvuil_080520.shp"):
        source = gpd.read_file('../data/shp/Inzameling_huisvuil_080520.shp')
    if area:
        source = source[source['sdcode'].isin(list(area))]
    return list(source.geometry)


def get_dataframe(q):
    """
    Make a request to Postgres database.

    General logging information needs to be submitted first
    Returns:
    - dataframe of result of SQL query
    """
    cnx = create_engine(postgres_str)
    query = q
    return pd.read_sql_query(query, cnx)


def load_api_data(prnt=False, subsectie=None):
    """
    Retrieve information from the garbage container API.

    This function loads in information on the current composition of container
    clusters in Amsterdam. It uses the API from data.amsterdam.nl (available at
    'https://api.data.amsterdam.nl/vsd/afvalclusters'). It returns the
    coordinates, amount and volume of different fractions and the address of
    the clusters. As a check, it is determined whether or not the cluster is
    currently active.
    Returns:
    - df containing coordinates, dict-like amount and volume per fraction and
    address.
    """
    x_coordinates = []
    y_coordinates = []
    aantal = []
    volumes = []
    adresses = []
    buurt = []

    link = 'https://api.data.amsterdam.nl/vsd/afvalclusters'

    try:  # Online scraping is preferred
        while link is not None:  # This is the case on the last page of the API
            if prnt:  # Can be used for some kind of monitoring of progres
                print(link)
            response = requests.get(link)
            output = response.json()
            for result in output['results']:
                # Als het cluster nog actief is
                if result['cluster_datum_einde_cluster'] is None:
                    x_coordinates.append(str(result['cluster_geometrie']
                                             ['coordinates'][0]))
                    y_coordinates.append(str(result['cluster_geometrie']
                                             ['coordinates'][1]))
                    aantal.append(result['cluster_fractie_aantal'])
                    volumes.append(result['cluster_fractie_volume'])
                    adresses.append(result['bag_adres_openbare_ruimte_naam'])
                    buurt.append(result['gbd_buurt_code'])

            link = output['_links']['next']['href']  # Link for next page

        df_clusters = pd.DataFrame([x_coordinates, y_coordinates, aantal,
                                    volumes, adresses, buurt]).T
        df_clusters = df_clusters.rename(columns={0: 'cluster_x',
                                                  1: 'cluster_y',
                                                  2: 'aantal_per_fractie',
                                                  3: 'volume_per_fractie',
                                                  4: 'street_name',
                                                  5: 'buurt'})
    except OSError:  # backup is online scraping is not working
        df_api = pd.read_csv('../Data/afval_cluster.csv', delimiter=';')
        df_api = df_api[df_api['cluster_datum_einde_cluster'].isna()]
        df_api = df_api[['cluster_geometrie', 'cluster_fractie_aantal',
                         'cluster_fractie_volume',
                         'bag_adres_openbare_ruimte_naam', 'gbd_buurt_code']]
        df_api['cluster_x'] = df_api['cluster_geometrie'] \
            .apply(lambda x: x.split('(')[1].split(' ')[0])
        df_api['cluster_y'] = df_api['cluster_geometrie'] \
            .apply(lambda x: x.split()[1][:-1])
        df_clusters = df_api.drop(['cluster_geometrie'], axis=1) \
            .rename(columns={'cluster_fractie_aantal': 'aantal_per_fractie',
                             'cluster_fractie_volume': 'volume_per_fractie',
                             'bag_adres_openbare_ruimte_naam': 'street_name',
                             'gbd_buurt_code': 'buurt'})

    # Transform coordinates of clusters to ints, as this helps easing join
    df_clusters['cluster_x'] = df_clusters['cluster_x'].astype('float')\
        .round(0).astype('int')
    df_clusters['cluster_y'] = df_clusters['cluster_y'].astype('float')\
        .round(0).astype('int')
    df_clusters['wijk'] = df_clusters['buurt'].str[:3]
    df_clusters['stadsdeel'] = df_clusters['buurt'].str[0]

    if subsectie:
        df_clusters = df_clusters[df_clusters['stadsdeel']
                                  .isin(list(subsectie))]
    return df_clusters


def get_db_afvalcluster_info():
    """
    Load POI information from postgres DB.

    Function that modifies loads in data on the garbage clusters from the
    Postgres database and modifies the resulting dataframe in a way that makes
    it usable for future analysis
    Returns:
    - pandas DataFrame containing all information from the database and also
    the added coordinates for the clusters and the type of POI
    """
    db_df = get_dataframe("""SELECT *
                             FROM proj_afval_netwerk.afv_rel_nodes_poi
                             """)
    db_df['woning'] = db_df['bk_afv_rel_nodes_poi'].str.split('~')
    db_df['cluster_x'] = db_df['woning'].apply(lambda x: x[0]).astype('float')\
        .round(0).astype('int')
    db_df['cluster_y'] = db_df['woning'].apply(lambda x: x[1]).astype('float')\
        .round(0).astype('int')
    db_df['type'] = db_df['woning'].apply(lambda x: x[2])
    db_df['bag'] = db_df['woning'].apply(lambda x: x[3])
    db_df = db_df.drop('woning', axis=1)
    return db_df


def get_distance_matrix():
    """
    Load distance matrix from postgres DB.

    Function to get the distance matrix. It returns the distance matrix sorted
    by distance in ascending order tos make it suitable for further use.
    """
    df_afstandn2 = get_dataframe("""SELECT *
                                FROM proj_afval_netwerk.afv_poi_afstand
                                WHERE afstand < 1000
                                """)
    return df_afstandn2


def create_all_households(rel_poi_df, subsectie=None):
    """
    Create a dataframe containing all households.

    This function takes as input the dataframe containing al POI's (both houses
    as well as container clusters) and returns a dataframe containing the
    information of all households. The optional parameter subsection determines
    if the entirety of addresses is to be used. If not, a certain stadsdeel can
    be returned.
    """
    polygon_list = load_geodata_containers(subsectie=subsectie)
    all_households = rel_poi_df[rel_poi_df['type'] != 'afval_cluster']
    all_households = all_households[['s1_afv_nodes', 'cluster_x', 'cluster_y']]
    all_households['uses_container'] = all_households\
        .apply(lambda row: address_in_service_area(row['cluster_x'],
                                                   row['cluster_y'],
                                                   polygon_list=polygon_list),
               axis=1)

    neighborhood_list = load_shapefile_neighborhood(area=subsectie)
    all_households['in_neigborhood'] = all_households\
        .apply(lambda row:
               address_in_service_area(row['cluster_x'], row['cluster_y'],
                                       polygon_list=neighborhood_list),
               axis=1)
    return all_households


def create_aansluitingen(good_result, total_join, use_count=False):
    """
    Create table showing number of users per fraction of container cluster.

    Function that returns dataframe aansluitingen that calculates amount of
    households per cluster and the percentage of overflow
    """
    if not use_count:
        aansluitingen = pd.DataFrame(good_result['poi_rest'].value_counts()).\
                join(pd.DataFrame(good_result['poi_papier'].value_counts()),
                     how='outer').\
                join(pd.DataFrame(good_result['poi_plastic'].value_counts()),
                     how='outer').\
                join(pd.DataFrame(good_result['poi_glas'].value_counts()),
                     how='outer').\
                join(pd.DataFrame(good_result['poi_textiel'].value_counts()),
                     how='outer')

    else:
        rest = pd.DataFrame(good_result.groupby('poi_rest')['count']
                            .sum()).rename(columns={'count': 'poi_rest'})
        plastic = pd.DataFrame(good_result.groupby('poi_plastic')['count']
                               .sum()).rename(columns={'count': 'poi_plastic'})
        papier = pd.DataFrame(good_result.groupby('poi_papier')['count']
                              .sum()).rename(columns={'count': 'poi_papier'})
        glas = pd.DataFrame(good_result.groupby('poi_glas')['count']
                            .sum()).rename(columns={'count': 'poi_glas'})
        textiel = pd.DataFrame(good_result.groupby('poi_textiel')['count']
                               .sum()).rename(columns={'count': 'poi_textiel'})
        aansluitingen = rest.join([plastic, papier, glas, textiel],
                                  how='outer')

    tmp_for_join = \
        total_join[['van_s1_afv_nodes', 'rest', 'papier', 'plastic', 'glas',
                    'textiel', 'totaal']].drop_duplicates()\
        .set_index('van_s1_afv_nodes')
    aansluitingen = aansluitingen.join(tmp_for_join, how='left')

    aansluitingen['rest_perc'] = \
        aansluitingen['poi_rest'] / aansluitingen['rest']
    aansluitingen['plastic_perc'] = \
        aansluitingen['poi_plastic'] / aansluitingen['plastic'] / 2
    aansluitingen['papier_perc'] = \
        aansluitingen['poi_papier'] / aansluitingen['papier'] / 2
    aansluitingen['glas_perc'] = \
        aansluitingen['poi_glas'] / aansluitingen['glas'] / 2
    aansluitingen['textiel_perc'] = \
        aansluitingen['poi_textiel'] / aansluitingen['textiel'] / 7.5

    return aansluitingen


def address_in_service_area(x, y, polygon_list=None, subsectie=None):
    """
    Determine if a adress POI is within the specified service area.

    function to see whether a certain household is within the service area of
    rest. The test criterion is a shapefile containing all places in the city
    of Amsterdam.
    Input is x and y coordinates of a house and a list of polygons of service
    area. If polygon_list is not given, it is created within the function. This
    makes the function more dynamic, but providing polygon_list increases
    speed.
    Returns boolean
    """
    if polygon_list is None:
        polygon_list = load_geodata_containers(subsectie=subsectie)
    point = shapely.geometry.Point(float(x), float(y))
    for polygon in polygon_list:
        if polygon.contains(point):
            return True
    return False


def distance_matrix_with_counts(get_data=True, inpt_dfob=None,
                                inpt_poi=None, inpt_dis=None,
                                use_old=False):
    """
    Retrieve distance matrix including the counts per address POI.

    Function that tries to match table with addresses per poi with
    information and subsequently with distance matrix to give back
    a distance matrix with the amount of households per addres poi.
    """
    if get_data:
        dfob = get_dataframe("""
                            SELECT bk_votpand_cluster, COUNT(*)
                            FROM proj_afval_netwerk
                                .rel_votpand_cluster_verblijfsobject
                            GROUP BY bk_votpand_cluster
                        """)
        df_afstandn2 = get_dataframe("""
                                    SELECT *
                                    FROM proj_afval_netwerk.afv_rel_nodes_poi
                                    """)
        df_afstandn = get_distance_matrix()

    if not get_data:
        dfob = inpt_dfob
        df_afstandn2 = inpt_poi
        df_afstandn = inpt_dis

    df_afstandn2['split'] = df_afstandn2['bk_afv_rel_nodes_poi'].str.split('~')
    df_afstandn2['x'] = df_afstandn2['split'].apply(lambda x: x[0])\
        .astype('float').round().astype('int')
    df_afstandn2['y'] = df_afstandn2['split'].apply(lambda x: x[1])\
        .astype('float').round().astype('int')
    df_afstandn2['type'] = df_afstandn2['split'].apply(lambda x: x[2])
    verblijfsobjecten = df_afstandn2[df_afstandn2['type'] != 'afval_cluster']
    verblijfsobjecten['bag'] = verblijfsobjecten['split'].apply(lambda x: x[3])\
        .astype('int64')

    if use_old:
        dfob['split'] = dfob['bk_votpand_cluster'].str.split('~')
        dfob['bag'] = dfob['split'].apply(lambda x: x[0]).astype('int64')
        dfob['x'] = dfob['split'].apply(lambda x: x[1]).astype('float').round()\
            .astype('int')
        dfob['y'] = dfob['split'].apply(lambda x: x[2]).astype('float').round().\
            astype('int')
        dfob = dfob.drop(['split'], axis=1)

        temp = dfob.set_index(['bag', 'x', 'y'])\
            .join(verblijfsobjecten.set_index(['bag', 'x', 'y']), how='outer',
                  lsuffix='_l').reset_index()
    else:
        df = pd.read_csv('../Data/households_per_cluster.csv')
        df1 = df[df['ligtin_bag_pnd_identificatie'].str.len() == 16]
        df2 = df[df['ligtin_bag_pnd_identificatie'].str.len() != 16]
        df2['ligtin_bag_pnd_identificatie'] = \
            df2['ligtin_bag_pnd_identificatie']\
            .str.split('|').map(lambda x: x[0])
        df = df1.append([df2])
        df['bag'] = df['ligtin_bag_pnd_identificatie'].astype('int64')
        df = df.drop(['ligtin_bag_pnd_identificatie'], axis=1)
        verblijfsobjecten = \
            df_afstandn2[df_afstandn2['type'] != 'afval_cluster']
        verblijfsobjecten['bag'] = verblijfsobjecten['bag'].astype('int64')
        temp = verblijfsobjecten.set_index('bag')\
            .join(df.set_index('bag'), how='left')
        temp['count'] = temp['aantal_woonfunctie']

    joined = temp.set_index('s1_afv_nodes')\
        .join(df_afstandn.set_index('naar_s1_afv_nodes'), how='outer')
    joined = joined.reset_index()[['van_s1_afv_nodes', 'index', 'afstand', 'count']].\
        rename(columns={'index': 'naar_s1_afv_nodes'}).sort_values(by='afstand').\
        reset_index().drop(['index'], axis=1).dropna()

    return joined

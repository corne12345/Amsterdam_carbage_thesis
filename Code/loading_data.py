import geopandas as gpd
from sqlalchemy import create_engine
import pandas as pd
import requests
from helper_functions import *


# Connect to Postgres database
# source: https://blog.panoply.io/connecting-jupyter-notebook-with-postgresql-for-python-data-analysis

# Postgres username, password, and database name
POSTGRES_ADDRESS = '10.243.25.5'
POSTGRES_PORT = '5432'
POSTGRES_USERNAME = 'heijne029'
# POSTGRES_PASSWORD = getpass(prompt='Password: ')
POSTGRES_PASSWORD = input()
POSTGRES_DBNAME = 'analyse_ruimte'

# A long string that contains the necessary Postgres login information
postgres_str = ('postgresql://{username}:{password}@{ipaddress}:{port}/{dbname}'
                .format(username=POSTGRES_USERNAME,
                        password=POSTGRES_PASSWORD,
                        ipaddress=POSTGRES_ADDRESS,
                        port=POSTGRES_PORT,
                        dbname=POSTGRES_DBNAME))



def load_geodata_containers():
    """
    This function loads in all polygons representing areas in the city of Amsterdam
    where general waste needs to be brought to a container. This is different
    from the alternative where general waste is collected from the sidewalk. This
    is needed to filter the address POI's to relevant POI's for optimization.

    Returns:
    - List of polygons making up the area of centralized garbage collection
    """

    source = gpd.read_file('../data/Inzameling_huisvuil_100220.shp')
    source = source[source['aanbiedwij'] == 'Breng uw restafval  naar een container voor restafval.']
    return list(source.geometry)


def get_dataframe(q):
    """
    Function to make a request to Postgres database.
    General logging information needs to be submitted first
    Returns:
    - dataframe of result of SQL query
    """
    cnx = create_engine(postgres_str)
    query=q
    return pd.read_sql_query(query,cnx)


def load_api_data(prnt=False):
    """
    This function loads in information on the current composition of container
    clusters in Amsterdam. It uses the API from data.amsterdam.nl (available at
    'https://api.data.amsterdam.nl/vsd/afvalclusters'). It returns the coordinates,
    amount and volume of different fractions and the address of the clusters. As
    a check, it is determined whether or not the cluster is currently active.
    Returns:
    - df containing coordinates, dict-like amount and volume per fraction and
    address.
    """
    x_coordinates = []
    y_coordinates = []
    aantal = []
    volumes = []
    adresses = []

    link = 'https://api.data.amsterdam.nl/vsd/afvalclusters'

    while link != None: #This is the case on the last page of the API
        if prnt: # Can be used for some kind of monitoring of progres
            print(link)
        response = requests.get(link)
        output = response.json()
        for result in output['results']:
            if result['cluster_datum_einde_cluster'] == None: #Als het cluster nog actief is
                x_coordinates.append(str(result['cluster_geometrie']['coordinates'][0]))
                y_coordinates.append(str(result['cluster_geometrie']['coordinates'][1]))
                aantal.append(result['cluster_fractie_aantal'])
                volumes.append(result['cluster_fractie_volume'])
                adresses.append(result['bag_adres_openbare_ruimte_naam'])
        try:
            link = output['_links']['next']['href'] #Retrieve link for next page
        except:
            link = None #True for last page of API

    df_clusters = pd.DataFrame([x_coordinates, y_coordinates, aantal, volumes, adresses]).T
    df_clusters = df_clusters.rename(columns={0: 'cluster_x', 1:'cluster_y', 2:'aantal_per_fractie', 3:'volume_per_fractie', 4: 'street_name'})
    # Transform coordinates of clusters to ints, as this helps easing join
    df_clusters['cluster_x'] = df_clusters['cluster_x'].astype('float').round(0).astype('int')
    df_clusters['cluster_y'] = df_clusters['cluster_y'].astype('float').round(0).astype('int')
    return df_clusters


def get_db_afvalcluster_info():
    """
    Function that modifies loads in data on the garbage clusters from the Postgres
    database and modifies the resulting dataframe in a way that makes it usable
    for future analysis
    Returns:
    - pandas DataFrame containing all information from the database and also the
    added coordinates for the clusters and the type of POI
    """
    db_df = get_dataframe("""SELECT *
                             FROM proj_afval_netwerk.afv_rel_nodes_poi
                             """)
    db_df['woning'] = db_df['bk_afv_rel_nodes_poi'].str.split('~')
    db_df['cluster_x'] = db_df['woning'].apply(lambda x: x[0]).astype('float').round(0).astype('int')
    db_df['cluster_y'] = db_df['woning'].apply(lambda x: x[1]).astype('float').round(0).astype('int')
    db_df['type'] = db_df['woning'].apply(lambda x: x[2])
    db_df['uses_container'] = db_df.apply(lambda row: address_in_service_area(row['cluster_x'], row['cluster_y']), axis=1)
    db_df = db_df.drop('woning', axis=1)
    return db_df


def get_distance_matrix():
    """
    Function to get the distance matrix. It returns the distance matrix sorted
    by distance in ascending order tos make it suitable for further use.
    """
    df_afstandn2 = get_dataframe("""SELECT *
                                FROM proj_afval_netwerk.afv_poi_afstand
                                WHERE afstand < 1000
                                """)
    return df_afstandn2


def create_all_households(rel_poi):
    """
    Function that creates a dataframe containing all households as rows
    """
    all_households = rel_poi_df[rel_poi_df['type']!='afval_cluster']
    all_households = all_households[['s1_afv_nodes', 'cluster_x', 'cluster_y']]
    all_households['uses_container'] = all_households.apply(lambda row: address_in_service_area(row['cluster_x'], row['cluster_y']), axis=1)
    return all_households

def create_aanlsuitingen(good_result, total_join):
    """
    Function that returns dataframe aansluitingen that calculates amount of
    households per cluster and the percentage of overflow
    """
    aansluitingen = pd.DataFrame(good_result['poi_rest'].value_counts()).\
                join(pd.DataFrame(good_result['poi_papier'].value_counts()), how='outer').\
                join(pd.DataFrame(good_result['poi_plastic'].value_counts()), how='outer').\
                join(pd.DataFrame(good_result['poi_glas'].value_counts()), how='outer').\
                join(pd.DataFrame(good_result['poi_textiel'].value_counts()), how='outer')

    tmp_for_join = total_join[['van_s1_afv_nodes', 'rest', 'papier', 'plastic', \
    'glas', 'textiel', 'totaal']].drop_duplicates().set_index('van_s1_afv_nodes')
    aansluitingen = aansluitingen.join(tmp_for_join, how='left')

    aansluitingen['rest_perc'] = aansluitingen['poi_rest'] / aansluitingen['rest']
    aansluitingen['plastic_perc'] = aansluitingen['poi_plastic'] / aansluitingen['plastic'] / 2
    aansluitingen['papier_perc'] = aansluitingen['poi_papier'] / aansluitingen['papier'] / 2
    aansluitingen['glas_perc'] = aansluitingen['poi_glas'] / aansluitingen['glas'] / 2
    aansluitingen['textiel_perc'] = aansluitingen['poi_textiel'] / aansluitingen['textiel'] / 7.5

    return aansluitingen

def address_in_service_area(x, y, polygon_list = None):
    """
    function to see whether a certain household is within the service area of rest.
    The test criterion is a shapefile containing all places in the city of
    Amsterdam
    Input is x and y coordinates of a house and a list of polygons of service area.
    If polygon_list is not given, it is created within the function. This makes
    the function more dynamic, but providing polygon_list increases speed.
    Returns boolean
    """
    if polygon_list == None:
        polygon_list = load_geodata_containers()
    point = shapely.geometry.Point(float(x),float(y))
    for polygon in polygon_list:
        if polygon.contains(point):
            return True
    return False

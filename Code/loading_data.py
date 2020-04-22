import geopandas as gpd
from sqlalchemy import create_engine




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
    x_coordinates = []
    y_coordinates = []
    aantal = []
    volumes = []
    adresses = []

    link = 'https://api.data.amsterdam.nl/vsd/afvalclusters'

    while link != None:
        if prnt:
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
            link = output['_links']['next']['href']
        except:
            link = None

    df_clusters = pd.DataFrame([x_coordinates, y_coordinates, aantal, volumes, adresses]).T
    df_clusters = df_clusters.rename(columns={0: 'cluster_x', 1:'cluster_y', 2:'aantal_per_fractie', 3:'volume_per_fractie', 4: 'street_name'})
    df_clusters['cluster_x'] = df_clusters['cluster_x'].astype('float').round(0).astype('int')
    df_clusters['cluster_y'] = df_clusters['cluster_y'].astype('float').round(0).astype('int')
    return df_clusters

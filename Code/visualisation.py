"""Code to visualise results of algorithms for display and analysis."""

import pandas as pd
import geopandas as gpd

from bokeh.plotting import figure, show
from bokeh.models import GeoJSONDataSource, ColumnDataSource, HoverTool

from .helper_functions import initial_loading


def visualise_configuration():
    """
    Create Bokeh Plot of candidate solution.

    Function prompts for filename to be plotted. It then loads in the current
    situation for comparison purposes. It plots the garbage container clusters
    and active addresses on a shapefile of the city. All places were garbage is
    centrally collected is marked in darker grey. The Bokeh Plot contains an
    interactive HoverTool that shows the compoisitions of either the houses or
    garbage containers.
    """
    filename = input("Please provide the requested filename")
    area = input("Provide Code of neighborhood (T/N/F/C)")
    if area == 'C':
        area = ['M', 'A', 'K', 'E']
    df_zo = pd.read_csv(filename)
    df_zo = df_zo.drop(['Unnamed: 0', 'Unnamed: 0.1'], axis=1)

    all_households, rel_poi_df, joined, df_afstandn2 = initial_loading()

    to_join = df_zo[['s1_afv_nodes', 'rest', 'plastic', 'papier', 'glas',
                     'textiel', 'totaal']].set_index('s1_afv_nodes')
    joined.s1_afv_nodes = joined.s1_afv_nodes.astype('int')
    new = to_join.join(joined.set_index('s1_afv_nodes'), lsuffix='_n')

    households_zo = all_households[all_households['in_neigborhood']]
    households_zo = households_zo.set_index('naar_s1_afv_nodes')\
        .join(df_afstandn2[['count', 'naar_s1_afv_nodes']]
              .set_index('naar_s1_afv_nodes'), how='left').drop_duplicates()

    load = gpd.read_file('../data/Inzameling_huisvuil_100220.shp')

    street_map = load[load['sdcode'].isin(list(area))]
    geosource = GeoJSONDataSource(geojson=street_map.to_json())
    street_map_clean = street_map[street_map['aanbiedwij'] ==
                                  "Breng uw restafval  naar een container" +
                                  "voor restafval."]
    geosource2 = GeoJSONDataSource(geojson=street_map_clean.to_json())

    TOOLTIPS = [
                ("index", "$index"),
                ("(x,y)", "($x, $y)"),
                ("Rest", "(@rest, @rest_n)"),
                ("Plastic", "(@plastic, @plastic_n)"),
                ("Papier", "(@papier, @papier_n)"),
                ("Glas", "(@glas, @glas_n)"),
                ("Textiel", "(@textiel, @textiel_n)")
                ]

    TOOLTIPS2 = [
                ("index", "$index"),
                ("(x,y)", "($x, $y)"),
                ("Count", "@count")]

    source1 = ColumnDataSource(data=new
                               [['cluster_x', 'cluster_y', 'rest', 'papier',
                                 'plastic', 'textiel', 'glas', 'rest_n',
                                 'papier_n', 'glas_n', 'plastic_n',
                                 'textiel_n']])
    source2 = ColumnDataSource(data=households_zo)

    p = figure()
    p.patches('xs', 'ys', source=geosource, fill_color='grey', alpha=0.1,
              line_color=None)
    p.patches('xs', 'ys', source=geosource2, fill_color='grey', alpha=0.3,
              line_color=None)
    r3 = p.circle(x='cluster_x', y='cluster_y', color='red', line_color=None,
                  source=source1, radius=20)
    p.add_tools(HoverTool(renderers=[r3], tooltips=TOOLTIPS))
    r4 = p.circle(x='cluster_x', y='cluster_y', radius=1.5, source=source2)
    p.add_tools(HoverTool(renderers=[r4], tooltips=TOOLTIPS2))

    show(p)
    return p


def plot_optimization(filename):
    """
    Plot penalty score vs. iterations combined with best average distance.

    This function takes a filename as input. This filename is a save of an
    optimization procedure. It plots the best column to see the penalty score
    in the amount of iterations. It then finds the avg_distance belonging to
    the current best score and also plots this. This plot is helpful for
    determining the best stopping strategy.
    """
    df_plot1 = pd.read_csv(filename)
    df_plot1['diff'] = df_plot1['penalties'] - df_plot1['best']
    # df_plot1['total'] = df_plot1['avg_distance'] + df_plot1['penalties']
    df_plot1['best_dist'] = df_plot1[df_plot1['diff'] < 0]['avg_distance']
    df_plot1['best_dist'] = df_plot1['best_dist'].fillna(method='ffill')
    ax = df_plot1['best_dist'].plot()
    ax = df_plot1['best'].plot(secondary_y=True)
    return ax

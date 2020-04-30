import pandas as pd
# import geopandas as gpd

from Code.helper_functions import initial_loading
from Code.algorithms import random_start_hillclimber


def main():
    all_households, rel_poi_df, joined, df_afstandn2 = initial_loading()
    hill_df, best_solution = random_start_hillclimber(joined, all_households, rel_poi_df, df_afstandn2)
    return

if __name__ == '__main__':
    main()

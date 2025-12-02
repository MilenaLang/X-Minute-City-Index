import os
import logging
import geopandas as gpd
import osmnx as ox
import pandas as pd
from pyproj import CRS
from shapely import box, Polygon
from xmin_core.utils.utils import (
    FacilitiesCategories, XMIN_Timeframse, geometry_to_single_point, MODE_SPEEDS, normalize_score, CATEGORY_BENCHMARKS,
)

log = logging.getLogger(__name__)

def get_city_pois_categories(buffered_polygon: Polygon, est_utm_crs: CRS, savedir:str='./tmp') -> dict:
    # get pois for each category,
    pois_cate_filenames = {}
    for category in FacilitiesCategories:
        log.info(f'Getting pois modes for {category.name}')
        tags = category.value  # dict
        most_pois_cate = ox.features.features_from_polygon(buffered_polygon, tags=tags)
        most_pois_cate = most_pois_cate[['geometry']]

        # convert multiple geometries to single point
        most_pois_cate = geometry_to_single_point(most_pois_cate, est_utm_crs)

        savename = os.path.join(savedir, f"most_pois_pts_{category.name}.gpkg")
        most_pois_cate.to_file(savename, driver='GPKG')
        pois_cate_filenames[category.name] = savename


    return pois_cate_filenames



def get_population_info_hex_grids(hexagons: gpd.GeoDataFrame, city_polygon: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    ##################
    # 1. get population from database
    ##################
    # TODO: import population data from database and aggregate to hex grids
    pops_city = None # e.g. db query based on city polygon

    ##################
    # 2. aggregate population to hex grids
    ##################
    intersection_gdf = gpd.overlay(hexagons, pops_city, how='intersection')

    # 2.1 Calculate area of overlap for each intersection
    intersection_gdf['overlap_area'] = intersection_gdf.area

    # 2.2 Calculate the total overlap area for each hexagon
    total_overlap_area = intersection_gdf.groupby('hex_id')['overlap_area'].sum().reset_index()
    total_overlap_area.rename(columns={'overlap_area': 'total_overlap_area'}, inplace=True)

    # 2.3 Merge total overlap area back into the intersection_gdf
    intersection_gdf = intersection_gdf.merge(total_overlap_area, on='hex_id')

    # 2.4 Calculate the proportion of each overlap area relative to the total overlap area
    intersection_gdf['area_weight'] = intersection_gdf['overlap_area'] / intersection_gdf['total_overlap_area']

    # 2.5 Calculate the area-weighted population contribution for each intersection
    intersection_gdf['weighted_population'] = intersection_gdf['area_weight'] * intersection_gdf['Einwohner']

    # 2.6 Sum the weighted populations to get the total population for each hexagon
    population_by_hex = intersection_gdf.groupby('hex_id')['weighted_population'].sum().reset_index()
    population_by_hex.rename(columns={'weighted_population': 'Einwohner'}, inplace=True)

    # 2.7 Merge the calculated population back into the hexagons dataframe
    hexagons_w_pop = hexagons.merge(population_by_hex, on='hex_id', how='left')

    # Filter out hexagons with no inhabitants
    hexagons_w_pop = hexagons_w_pop[
        (hexagons_w_pop['Einwohner'].notnull()) & (hexagons_w_pop['Einwohner'] != 0)
        ]

    ##################
    # 3. set population-related attributes
    ##################
    hexagons_w_pop.rename(columns={'Einwohner': 'living'}, inplace=True)
    hexagons_w_pop['living'] = hexagons_w_pop['living'].fillna(0)

    return hexagons_w_pop


def get_xmin_index_score(
    hex_grids: gpd.GeoDataFrame,
    pois_cnt_cates_files:dict,
    savedir:str,
    is_normalize:bool = True,
):
    modes = MODE_SPEEDS.keys()

    savedir = os.path.join(savedir, 'index_score')
    os.makedirs(savedir, exist_ok=True)

    # re-organize pois_cnt based on their modes and times.
    pois_cnt_modes_times = {f'{m[:4]}_{t}': [] for m in modes for t in XMIN_Timeframse }
    for name_cate, pois_cnt_cate_files in pois_cnt_cates_files.items():
        for pois_cnt_cate_mode_time_file in pois_cnt_cate_files:
            # get current category's mode and timeframe key.
            pois_cnt_c_m_t_file_sp = os.path.basename(pois_cnt_cate_mode_time_file)[:-4].split('_')
            xmin_mode, xmin_time = pois_cnt_c_m_t_file_sp[0], pois_cnt_c_m_t_file_sp[-1]
            key_mode_time = f'{xmin_mode[:4]}_{xmin_time}'

            # read file
            pois_cnt_cate_mode_time = pd.read_csv(pois_cnt_cate_mode_time_file)
            # normalize
            if is_normalize:
                pois_cnt_cate_mode_time[f'{name_cate}_normalized'] = normalize_score(
                    pois_cnt_cate_mode_time[name_cate].values,
                    CATEGORY_BENCHMARKS[name_cate],
                )

            # add one category_mode_time situation's pois_cnt to corresponding list
            pois_cnt_cate_mode_time.set_index('hex_id', inplace=True)
            pois_cnt_modes_times[key_mode_time].append(pois_cnt_cate_mode_time)


    # get score results: filenum = num_modes (e.g. cycle, foot) * num_timeframes (e.g. 15,20,25)
    normalized_columns = [f'{category}_normalized' for category in CATEGORY_BENCHMARKS.keys()]
    for key_mode_time, pois_cnt_mode_time in pois_cnt_modes_times.items():
        pois_cnt_mode_time = pd.concat(pois_cnt_mode_time, axis=1)
        hex_grids_w_pois = hex_grids.merge(pois_cnt_mode_time, on='hex_id', how='left')

        # get total score
        hex_grids_w_pois['score'] = hex_grids_w_pois[normalized_columns].sum(axis=1) / len(CATEGORY_BENCHMARKS)# TODO: check why it's .mean in original code.

        # save result
        savename = os.path.join(savedir, f'{key_mode_time}.gpkg')
        hex_grids_w_pois.to_file(savename, driver='GPKG')


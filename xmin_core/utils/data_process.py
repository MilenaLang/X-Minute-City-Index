import logging

import geopandas as gpd
import h3
import numpy as np
import osmnx as ox
import pandas as pd
from pyproj import CRS
from shapely import Polygon, MultiPolygon, box

from xmin_core.utils.utils import BUFFER_DISTANCES, HEX_RESOLUTION, area_ratio_within_city

log = logging.getLogger(__name__)


def get_city_bboxes(city_name:str) -> tuple[gpd.GeoDataFrame, pd.DataFrame, CRS]:
    city_polygon = ox.geocode_to_gdf(city_name) # Get geometry for the place a geodataframe
    buffered_bounds, est_utm_crs = get_bboxes_mode_time(city_polygon)

    return city_polygon, buffered_bounds, est_utm_crs


def get_bboxes_mode_time(city_polygon: gpd.GeoDataFrame) -> tuple[pd.DataFrame, CRS]:
    # reproject to metric
    estimated_crs= city_polygon.estimate_utm_crs()  # guess the UTM zone
    city_polygon_projected = city_polygon.to_crs(estimated_crs)

    # Get the bbox of the reprjected city
    minx, miny, maxx, maxy = city_polygon_projected.total_bounds
    bounding_box = box(minx, miny, maxx, maxy)

    # get the buffered bounds for each mode and timeframe
    buffered_bounds = []

    pd_modetime = pd.DataFrame(BUFFER_DISTANCES)
    pd_modetime['geometry'] = bounding_box
    time_gpd = gpd.GeoDataFrame(pd_modetime, geometry='geometry', crs=estimated_crs)
    time_gpd['timeframe'] = time_gpd.index
    for mode, time_dict in BUFFER_DISTANCES.items():
        # buffer each timeframe by the corresponding distance
        buffered_bbox_mode = time_gpd.geometry.buffer(time_gpd[mode]).to_crs(epsg=4326).bounds # minx, miny, maxx, maxy
        buffered_bbox_mode['mode'] = mode # minx, miny, maxx, maxy, mode
        buffered_bbox_mode['timeframe'] = buffered_bbox_mode.index

        buffered_bounds.append(buffered_bbox_mode)

    buffered_bounds = pd.concat(buffered_bounds) # .set_index(['mode', 'timeframe'])
    log.debug(f"bounds: {buffered_bounds}")

    return buffered_bounds, estimated_crs


def get_hex_grids(city_polygon: gpd.GeoDataFrame, savedir:str='./tmp') -> gpd.GeoDataFrame:
    # use h3 to create hex_grids
    city_polygon_h3 = h3.geo_to_h3shape(city_polygon.union_all())
    hexagons = h3.polygon_to_cells_experimental(city_polygon_h3, res=HEX_RESOLUTION, contain='center')

    # Convert hexagons to GeoJSON features with hex_id
    hexagon_features = [
        {
            "type": "Feature",
            "properties": {"hex_id": hex_id},
            "geometry": {
                "type": "Polygon",
                "coordinates": [np.asarray(h3.cell_to_boundary(hex_id))[:, [1, 0]].tolist()],
            },
        }
        for hex_id in hexagons
    ]

    # Create a GeoDataFrame from the features
    hexagons_gdf = gpd.GeoDataFrame.from_features(hexagon_features, crs=4326)

    return hexagons_gdf


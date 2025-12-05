import os
from dataclasses import dataclass

import geopandas as gpd
import pandas as pd
from geoalchemy2 import WKTElement

from sqlalchemy import MetaData, create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool


@dataclass
class DatabaseConnection:
    engine: Engine
    metadata: MetaData


def open_db(db_link: str) -> DatabaseConnection:
    engine = create_engine(db_link, echo=False, plugins=['geoalchemy2'], poolclass=NullPool)
    metadata = MetaData()
    metadata.reflect(bind=engine)

    db_conn = DatabaseConnection(engine=engine, metadata=metadata)
    return db_conn


def conn_ca_db(env_name:str) -> DatabaseConnection:
    ca_db_link = os.getenv(env_name)
    ca_db_conn = open_db(ca_db_link)

    if not ca_db_conn:
        raise ValueError("CA database is not available.")
    return ca_db_conn



def query_by_aoi(db_table, aoi = None, crs:int=4326):
    if aoi is None: # entire Germany
        query = select(db_table) # return all data
    else: # special cities
        aoi_geom = WKTElement(aoi.wkt, srid=crs)
        query = select(db_table).where(db_table.c.geometry.op('&&')(aoi_geom) & db_table.c.geometry.ST_Within(aoi_geom))

    return query


def queryres2gdf(result, crs:str, indexcol:str) -> gpd.GeoDataFrame:
    result_gdf = pd.DataFrame(result)
    result_gdf['geometry'] = gpd.GeoSeries.from_wkb(result_gdf['geometry'].astype(str))
    result_gdf = gpd.GeoDataFrame(result_gdf, crs=f'{crs}').set_index(indexcol)

    return result_gdf
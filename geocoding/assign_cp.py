"""
Asigna a cada anuncio su código postal mediante point-in-polygon.

Para cada data/raw/properties_<Estado>.csv usa los polígonos de
geojson_with_names/cp_<Estado>.geojson y guarda data/geocoded/geocoded_<Estado>.csv
con las columnas originales más:
    - codigo_postal: CP a 5 dígitos (texto, conserva el 0 inicial).
    - cp_metodo: "within" si el punto cae dentro del polígono,
                 "nearest" si se asignó el polígono más cercano (<= cp_max_distancia_m),
                 vacío si no se pudo asignar (sin coordenadas o demasiado lejos).

Ejecutar desde la raíz del repositorio:
    python -m geocoding.assign_cp
"""
import geopandas as gpd
import pandas as pd

from config.config import crs_metrico, cp_max_distancia_m
from config.paths import RAW_DATA, GEOJSON_CP, GEOCODED_DATA
from src.utils import extraer_sufijo_csv

columns_to_save_in_geodata = [
"price",
"currency",
"property_type",
"location",
"neighborhood",
"city",
"state",
"latitude",
"longitude",
"bedrooms",
"bathrooms",
"built_m2",
"land_m2",
"parking",
"maintenance_expenses",
"antiquity_years",
"publication_age",
"views_count",
"published_date",
"scraped_at",
"source_page",
"codigo_postal",
"cp_metodo"
]

def load_cp_polygons(state_name: str) -> gpd.GeoDataFrame:
    polygons = gpd.read_file(GEOJSON_CP / f"cp_{state_name}.geojson", columns=["d_codigo"])
    #Algunos polígonos vienen inválidos (auto-intersecciones); se reparan solo esos
    invalid = ~polygons.is_valid
    polygons.loc[invalid, "geometry"] = polygons.loc[invalid].make_valid(method="structure")
    polygons["codigo_postal"] = polygons["d_codigo"].astype(int).astype(str).str.zfill(5)
    return polygons[["codigo_postal", "geometry"]]


def assign_cp(df: pd.DataFrame,
              polygons: gpd.GeoDataFrame,
              max_distance_m: float = cp_max_distancia_m) -> pd.DataFrame:

    result = df.copy()
    result["codigo_postal"] = pd.NA
    result["cp_metodo"] = pd.NA

    has_coords = result[["latitude", "longitude"]].notna().all(axis=1)
    points = gpd.GeoDataFrame(
        result.loc[has_coords, []],
        geometry=gpd.points_from_xy(result.loc[has_coords, "longitude"],
                                    result.loc[has_coords, "latitude"]),
        crs="EPSG:4326",
    )

    #1. Point-in-polygon
    within = gpd.sjoin(points, polygons, how="inner", predicate="within")
    within = within[~within.index.duplicated()]
    result.loc[within.index, "codigo_postal"] = within["codigo_postal"]
    result.loc[within.index, "cp_metodo"] = "within"

    #2. Puntos fuera de todo polígono (huecos entre polígonos, bordes): CP más cercano
    outside = points.loc[points.index.difference(within.index)]
    if len(outside):
        nearest = gpd.sjoin_nearest(outside.to_crs(crs_metrico),
                                    polygons.to_crs(crs_metrico),
                                    how="inner",
                                    max_distance=max_distance_m)
        nearest = nearest[~nearest.index.duplicated()]
        result.loc[nearest.index, "codigo_postal"] = nearest["codigo_postal"]
        result.loc[nearest.index, "cp_metodo"] = "nearest"

    return result


def geocode_state(raw_data_path) -> pd.DataFrame:
    state_name = extraer_sufijo_csv(raw_data_path)
    geocoded = assign_cp(pd.read_csv(raw_data_path), load_cp_polygons(state_name))
    GEOCODED_DATA.mkdir(parents=True, exist_ok=True)
    geocoded[columns_to_save_in_geodata].to_csv(GEOCODED_DATA / f"geocoded_{state_name}.csv", index=False)
    return geocoded


def main():
    summary = []
    for raw_data_path in sorted(RAW_DATA.glob("properties_*.csv")):
        geocoded = geocode_state(raw_data_path)
        metodo = geocoded["cp_metodo"].value_counts()
        summary.append({"estado": extraer_sufijo_csv(raw_data_path),
                        "anuncios": len(geocoded),
                        "within": metodo.get("within", 0),
                        "nearest": metodo.get("nearest", 0),
                        "sin_cp": geocoded["codigo_postal"].isna().sum()})

    summary = pd.DataFrame(summary)
    print(summary.to_string(index=False))
    print(f"\nCon CP: {1 - summary['sin_cp'].sum() / summary['anuncios'].sum():.2%} "
          f"de {summary['anuncios'].sum()} anuncios. Resultados en {GEOCODED_DATA}")


if __name__ == "__main__":
    main()

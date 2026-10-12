"""
Ranking global por colonia y código postal a partir de los datos geocodificados.

Reutiliza los pasos de src.pipeline.full_treatment (preprocesado, filtro de fecha,
precio/m2, IQR, edad, agrupación, corte por mínimo de anuncios y score), pero:
    - lee data/geocoded/geocoded_<Estado>.csv en lugar de data/raw,
    - agrupa por estado, ciudad, municipio, colonia y código postal,
    - normaliza sobre el conjunto global (todas las entidades juntas).

El municipio se toma del polígono del CP (geojson_with_names/cp_<Estado>.geojson);
la ciudad es la columna "city" del anuncio.

Ejecutar desde la raíz del repositorio:
    python global_norm_cp.py
"""
import geopandas as gpd
import pandas as pd

from config.config import min_ads_cp
from config.paths import GEOCODED_DATA, GEOJSON_CP, SCORED_DATA
from src.clean import add_age_column, add_price_m2, filter_iqr, group_by_colonia
from src.preprocessing import filter_date, preprocess
from src.score import minmax_columns, pavc_score, qs_score
from src.utils import extraer_sufijo_csv

columns_geocoded = ["city",
                    "neighborhood",
                    "codigo_postal",
                    "price",
                    "currency",
                    "built_m2",
                    "published_date",
                    "scraped_at"]

columns_geocoded_not_null = ["neighborhood",
                             "codigo_postal",
                             "price",
                             "built_m2"]

columns_geocoded_renamed = ["ciudad",
                            "colonia",
                            "codigo_postal",
                            "precio",
                            "construidos_m2",
                            "fecha_publi",
                            "fecha_scrap"]

group_columns = ["estado", "ciudad", "municipio", "colonia", "codigo_postal"]
colonia_columns = ["estado", "ciudad", "colonia"]


def load_cp_municipios(state_name: str) -> pd.DataFrame:
    cps = gpd.read_file(GEOJSON_CP / f"cp_{state_name}.geojson",
                        columns=["d_codigo", "municipio"],
                        ignore_geometry=True)
    cps["codigo_postal"] = cps["d_codigo"].astype(int).astype(str).str.zfill(5)
    #Algunos CP traen el municipio vacío ("[ ]"); se deja en blanco para no perder esos anuncios al agrupar
    cps["municipio"] = cps["municipio"].fillna("").replace("[ ]", "")
    return cps[["codigo_postal", "municipio"]].drop_duplicates("codigo_postal")


def group_state(geocoded_path, min_ads_cp: int = min_ads_cp) -> pd.DataFrame:
    """Limpia un estado y lo agrupa por colonia y CP (mismos pasos que full_treatment)."""
    state_name = extraer_sufijo_csv(geocoded_path)

    prep_data = filter_date(preprocess(geocoded_path,
                                       columns_maintain=columns_geocoded,
                                       not_null_columns=columns_geocoded_not_null,
                                       new_names=columns_geocoded_renamed),
                            date_column="fecha_publi")
    #preprocess lee el CP como número: se recupera el 0 inicial
    prep_data["codigo_postal"] = prep_data["codigo_postal"].astype(int).astype(str).str.zfill(5)
    prep_data = prep_data.merge(load_cp_municipios(state_name), on="codigo_postal", how="left")
    prep_data.insert(0, "estado", state_name)

    add_price_m2(prep_data)
    clean_data = filter_iqr(prep_data, ["precio_m2"])
    add_age_column(clean_data)

    grouped = group_by_colonia(clean_data, by=group_columns)

    #Proporción de los anuncios de la colonia que caen en cada CP (antes del corte)
    grouped["proporcion"] = grouped["conteo"] / grouped.groupby(colonia_columns)["conteo"].transform("sum")

    return grouped[grouped["conteo"] >= min_ads_cp]


def build_global_ranking_cp() -> pd.DataFrame:
    """Agrupa todos los estados geocodificados, normaliza sobre el conjunto global y guarda el resultado."""
    files = sorted(GEOCODED_DATA.glob("geocoded_*.csv"))
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos geocoded_*.csv en {GEOCODED_DATA}")

    grouped = pd.concat([group_state(file) for file in files], ignore_index=True)
    normalized = minmax_columns(
        grouped,
        {
            "precio_m2_mediana": (0, 1),
            "precio_m2_cv": (1, 0),
            "edad_dias_promedio": (1, 0),
            "ln(1+n)": (0, 1),
        },
    )
    normalized = qs_score(pavc_score(normalized))
    normalized["precio_m2"] = grouped["precio_m2_mediana"]
    SCORED_DATA.mkdir(parents=True, exist_ok=True)
    output_path = SCORED_DATA / "global_norm_cp.csv"
    normalized.to_csv(output_path, index=False)
    print(f"Ranking global por CP guardado en {output_path} ({len(normalized)} colonia-CP)")
    return normalized


if __name__ == "__main__":
    build_global_ranking_cp()

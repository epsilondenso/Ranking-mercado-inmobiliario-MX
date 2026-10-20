"""
Ranking global por colonia, ubicada en su código postal principal, a partir de los datos geocodificados.

Reutiliza los pasos de src.pipeline.full_treatment (preprocesado, filtro de fecha,
precio/m2, IQR, edad, agrupación, corte por mínimo de anuncios y score), pero:
    - lee data/geocoded/geocoded_<Estado>.csv en lugar de data/raw,
    - calcula las métricas por colonia (estado, ciudad, colonia) con todos sus anuncios,
      sin partirla por CP, así que coinciden con las de la versión por estado,
    - asigna cada colonia a un solo CP: el que concentra más de sus anuncios (CP principal),
    - normaliza sobre el conjunto global (todas las entidades juntas).

El municipio se toma del polígono del CP principal (geojson_with_names/cp_<Estado>.geojson);
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

#El CP no es obligatorio: los anuncios sin CP cuentan en las métricas de su colonia (igual que en la versión por estado)
columns_geocoded_not_null = ["neighborhood",
                             "price",
                             "built_m2"]

columns_geocoded_renamed = ["ciudad",
                            "colonia",
                            "codigo_postal",
                            "precio",
                            "construidos_m2",
                            "fecha_publi",
                            "fecha_scrap"]

colonia_columns = ["estado", "ciudad", "colonia"]


def load_cp_municipios(state_name: str) -> pd.DataFrame:
    cps = gpd.read_file(GEOJSON_CP / f"cp_{state_name}.geojson",
                        columns=["d_codigo", "municipio"],
                        ignore_geometry=True)
    cps["codigo_postal"] = cps["d_codigo"].astype(int).astype(str).str.zfill(5)
    #Algunos CP traen el municipio vacío ("[ ]"); se deja en blanco
    cps["municipio"] = cps["municipio"].fillna("").replace("[ ]", "")
    return cps[["codigo_postal", "municipio"]].drop_duplicates("codigo_postal")


def principal_cp(clean_data: pd.DataFrame) -> pd.DataFrame:
    """CP con más anuncios de cada colonia (en empate, el menor), su conteo y la fracción de la colonia que representa."""
    with_cp = clean_data[clean_data["codigo_postal"].notna()]
    counts = with_cp.groupby(colonia_columns + ["codigo_postal"]).size().rename("conteo_cp").reset_index()
    counts["proporcion_cp_colonia"] = counts["conteo_cp"] / counts.groupby(colonia_columns)["conteo_cp"].transform("sum")
    counts = counts.sort_values(colonia_columns + ["conteo_cp", "codigo_postal"],
                                ascending=[True] * len(colonia_columns) + [False, True])
    return counts.drop_duplicates(colonia_columns)


def group_state(geocoded_path, min_ads_cp: int = min_ads_cp) -> pd.DataFrame:
    """Limpia un estado, lo agrupa por colonia y ubica cada colonia en su CP principal."""
    state_name = extraer_sufijo_csv(geocoded_path)

    prep_data = filter_date(preprocess(geocoded_path,
                                       columns_maintain=columns_geocoded,
                                       not_null_columns=columns_geocoded_not_null,
                                       new_names=columns_geocoded_renamed),
                            date_column="fecha_publi")
    #preprocess lee el CP como número: se recupera el 0 inicial
    has_cp = prep_data["codigo_postal"].notna()
    prep_data["codigo_postal"] = prep_data["codigo_postal"].astype(object)
    prep_data.loc[has_cp, "codigo_postal"] = prep_data.loc[has_cp, "codigo_postal"].astype(int).astype(str).str.zfill(5)
    prep_data.insert(0, "estado", state_name)

    add_price_m2(prep_data)
    clean_data = filter_iqr(prep_data, ["precio_m2"])
    add_age_column(clean_data)

    grouped = group_by_colonia(clean_data, by=colonia_columns)
    grouped = grouped[grouped["conteo"] >= min_ads_cp]

    #Las colonias sin ningún anuncio con CP no se pueden ubicar en el mapa y se descartan
    grouped = grouped.merge(principal_cp(clean_data), on=colonia_columns, how="inner")
    grouped = grouped.merge(load_cp_municipios(state_name), on="codigo_postal", how="left")
    grouped["municipio"] = grouped["municipio"].fillna("")

    return grouped


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
    #Orden de columnas: identificación, ubicación en el CP principal y métricas
    first = ["estado", "ciudad", "municipio", "colonia", "codigo_postal",
             "conteo", "conteo_cp", "proporcion_cp_colonia"]
    normalized = normalized[first + [c for c in normalized.columns if c not in first]]
    SCORED_DATA.mkdir(parents=True, exist_ok=True)
    output_path = SCORED_DATA / "global_norm_cp.csv"
    normalized.to_csv(output_path, index=False)
    print(f"Ranking global por colonia y CP principal guardado en {output_path} ({len(normalized)} colonias)")
    return normalized


if __name__ == "__main__":
    build_global_ranking_cp()

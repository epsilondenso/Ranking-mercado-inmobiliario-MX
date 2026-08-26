import pandas as pd
import numpy as np
from config.config import fecha_scrap

def filter_iqr(df:pd.DataFrame, columns:list[str] = ["precio_m2"]):

    def filter_one_column(df:pd.DataFrame, column: str):
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        limite_inferior = Q1 - 1.5 * IQR
        limite_superior = Q3 + 1.5 * IQR
        return df.loc[(df[column] >= limite_inferior) & (df[column] <= limite_superior)].copy()
    
    filtered = df.copy()
    for column in columns:
        filtered = filter_one_column(filtered, column)
    return filtered

def add_price_m2(df: pd.DataFrame) -> pd.DataFrame | None:

    df["precio_m2"] = df["precio"]//df["construidos_m2"]

def add_age_column(
    df: pd.DataFrame,
    column_publi: str = "fecha_publi",
    column_scrap: str = "fecha_scrap",
    inplace: bool = True
) -> pd.DataFrame | None:

    #fecha = pd.Timestamp(fecha_scrap)

    #CONVERTIR A DATETIME
    df[column_publi] = pd.to_datetime(
    df[column_publi],
    errors="coerce"
    ).dt.tz_localize(None)

    df[column_scrap] = pd.to_datetime(
    df[column_scrap],
    errors="coerce"
    ).dt.tz_localize(None)
    
    #CALCULAR EDAD EN DÍAS
    df.loc[:, "edad_dias"] = (
        df[column_scrap] - df[column_publi]
    ).dt.days

    if inplace:
        return None

    return df

def group_by_colonia(df: pd.DataFrame, by: list[str] = ['municipio', 'colonia']) -> pd.DataFrame:

    tabla_agrupada = df.groupby(by).agg(
    conteo=('precio_m2', 'count'),
    precio_m2_mediana=('precio_m2', 'median'),
    precio_m2_promedio=('precio_m2', 'mean'),
    precio_m2_std=('precio_m2', 'std'),
    edad_dias_promedio=('edad_dias', 'mean')
    ).reset_index()

    # 2. Reemplazar valores NaN en la Desviación Estándar (sucede si una colonia solo tiene 1 anuncio)
    tabla_agrupada['precio_m2_std'] = tabla_agrupada['precio_m2_std'].fillna(0)

    # 3. Calcular el Coeficiente de Variación (CV) de una vez
    # (CV = Desviación Estándar / Promedio)
    tabla_agrupada['precio_m2_cv'] = (
    tabla_agrupada['precio_m2_std'] / tabla_agrupada['precio_m2_promedio']
    ).fillna(0)

    #4. Añadir columna ln(1 + count)
    tabla_agrupada["ln(1+n)"] = np.log(1 + tabla_agrupada["conteo"])
    return tabla_agrupada 


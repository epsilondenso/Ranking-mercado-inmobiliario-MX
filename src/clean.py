import pandas as pd
from config.config import fecha_scrap

def filter_iqr(df:pd.DataFrame, column:str = "precio_m2"):

    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    limite_inferior = Q1 - 1.5 * IQR
    limite_superior = Q3 + 1.5 * IQR
    
    return df.loc[(df[column] >= limite_inferior) & (df[column] <= limite_superior)].copy()

def add_price_m2(df: pd.DataFrame) -> pd.DataFrame | None:

    df["precio_m2"] = df["precio"]//df["construidos_m2"]

def add_age_column(
    df: pd.DataFrame,
    column_name: str = "fecha_publi",
    inplace: bool = True
) -> pd.DataFrame | None:

    fecha = pd.Timestamp(fecha_scrap)

    df.loc[:, "edad_dias"] = (
        fecha - df[column_name]
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
    return tabla_agrupada 
    
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from config.config import (pesos_pavcscore, 
                           columns_score,
                           qs_weights, 
                           q_columns, 
                           q_weights,
                           s_columns, 
                           s_weights)

def minmax_columns(
    df: pd.DataFrame,
    feature_ranges: dict[str, tuple[float, float]]
) -> pd.DataFrame:

    df_normalized = df.copy()

    for column, feature_range in feature_ranges.items():

        scaler = MinMaxScaler(feature_range=(0, 1))

        values = scaler.fit_transform(
            df[[column]]
        ).ravel()

        if feature_range == (1, 0):
            values = 1 - values

        df_normalized[column] = values

    return df_normalized

def pavc_score(df: pd.DataFrame, columns: list[str] = columns_score) -> pd.DataFrame:
    weights = pesos_pavcscore
    score = df.copy()
    score["pavc_score"] =  weights[0]*score[columns[0]] + weights[1]*score[columns[1]] + weights[2]*score[columns[2]]

    return score

def qs_score(df: pd.DataFrame, 
             weights: list[float] = qs_weights, 
             q_columns: list[str] = q_columns,
             q_weights: list[float] = q_weights,
             s_columns: list[str] = s_columns,
             s_weights: list[float] = s_weights) -> pd.DataFrame:

    score = df.copy()

    # Componente de calidad
    score["Q"] = sum(
        w * score[col]
        for col, w in zip(q_columns, q_weights)
    )

    # Componente de tamaño del mercado
    score["S"] = sum(
        w * score[col]
        for col, w in zip(s_columns, s_weights)
    )

    # Score final
    score["qs_score"] = (
        weights[0] * score["Q"] +
        weights[1] * score["S"]
    )

    return score
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from config.config import pesos_score, columns_score

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

def score(df: pd.DataFrame, columns: list[str] = columns_score) -> pd.DataFrame:

    score = df.copy()
    score["score"] =  pesos_score[0]*score[columns[0]] + pesos_score[1]*score[columns[1]] + pesos_score[2]*score[columns[2]]

    return score
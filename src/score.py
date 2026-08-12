import pandas as pd
from sklearn.preprocessing import MinMaxScaler


import pandas as pd
from sklearn.preprocessing import MinMaxScaler


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
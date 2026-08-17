import pandas as pd
from config.config import columns_to_maintain, columns_not_null, columns_renamed, tipo_cambio


def convert_usd_to_mxn(df: pd.DataFrame, price_usd: float = tipo_cambio):


    df["price"] = df["price"].astype(float)
    df.loc[df["currency"] == "USD", "price"] *= tipo_cambio
    df.loc[df["currency"] == "USD", "currency"] = "MXN"
    df["price"] = df["price"].astype("int64")
    return df 

def preprocess(file_path: str, rename_columns:bool = True, output_path:str|None = None, save: bool = False, ) -> pd.DataFrame:

    data = pd.read_csv(file_path)[columns_to_maintain].drop_duplicates().dropna(subset = columns_not_null)
    data = convert_usd_to_mxn(data).drop(columns = ["currency"])
    if rename_columns:
        data.columns = columns_renamed

    if save:
        data.to_csv(output_path, index = False)

    return data

def filter_date(df: pd.DataFrame, min_year: int = 2024, date_column: str = "published_date") -> pd.DataFrame:

    df[date_column] = [date[:10] for date in df[date_column]]
    df[date_column] = pd.to_datetime(df[date_column])
    df[df[date_column].dt.year > min_year]

    return df

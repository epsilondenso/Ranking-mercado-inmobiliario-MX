import pandas as pd
from config.config import columns_to_maintain, columns_not_null, columns_renamed, tipo_cambio


def convert_usd_to_mxn(df: pd.DataFrame, price_usd: float = tipo_cambio):


    df["price"] = df["price"].astype(float)
    df.loc[df["currency"] == "USD", "price"] *= price_usd
    df.loc[df["currency"] == "USD", "currency"] = "MXN"
    df["price"] = df["price"].astype("int64")
    return df 

def preprocess(file_path: str, 
               columns_maintain: list[str] = columns_to_maintain,
               not_null_columns: list[str] = columns_not_null,
               rename_columns:bool = True,
               new_names: list[str] = columns_renamed, 
               output_path:str|None = None, 
               save: bool = False) -> pd.DataFrame:

    data = pd.read_csv(file_path)[columns_maintain].drop_duplicates().dropna(subset = not_null_columns)
    data = convert_usd_to_mxn(data).drop(columns = ["currency"])
    if rename_columns:
        data.columns = new_names

    if save:
        data.to_csv(output_path, index = False)
    return data

def filter_date(df: pd.DataFrame, min_year: int = 2024, date_column: str = "published_date") -> pd.DataFrame:

    df[date_column] = [date[:10] for date in df[date_column]]
    df[date_column] = pd.to_datetime(df[date_column])
    

    return df[df[date_column].dt.year > min_year]

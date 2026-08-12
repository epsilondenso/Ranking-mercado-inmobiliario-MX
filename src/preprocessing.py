import pandas as pd
from config.config import columns_to_maintain, columns_not_null, columns_renamed

def drop_dup_null(file_path: str, rename_columns:bool = True, output_path:str|None = None, save: bool = False, ) -> pd.DataFrame:

    data = pd.read_csv(file_path)[columns_to_maintain].drop_duplicates().dropna(subset = columns_not_null)

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

#Terceros
import pandas as pd
#import numpy as np
#import matplotlib.pyplot as plt
#from sklearn.preprocessing import MinMaxScaler
#Este proyecto
from config.paths import SCORED_DATA, CLEAN_DATA, GROUPED_DATA
#from config.config import pesos_score
from src.preprocessing import drop_dup_null, filter_date
from src.clean import filter_iqr, add_age_column, add_price_m2, group_by_colonia
from src.score import minmax_columns, score
from src.utils import extraer_sufijo_csv


def full_treatment(raw_data_path: str) -> pd.DataFrame:

    """
    Preprocess, cleans, normalizes and computes the score 


    PARAMETERS:
        - raw_data_path: str. Must be in the form "directory/any_nombreestado.csv"
    RETURNS:
        - normalized: pd.DataFrame.
    """

    state_name = extraer_sufijo_csv(raw_data_path)

    #load
    prep_data = filter_date(drop_dup_null(raw_data_path), date_column= "fecha_publi")
    #Add price/m2
    add_price_m2(prep_data)
    #Drop outliers
    clean_data = filter_iqr(prep_data, "precio_m2")
    #Add age column (days between add publication date and scrap date)
    add_age_column(clean_data)
    #save clean
    clean_data[["municipio", "colonia", "precio_m2", "edad_dias"]].to_csv(CLEAN_DATA / f"clean_{state_name}.csv", index = False)
    #GROUP_BY_COLONIA
    grouped = group_by_colonia(clean_data)
    #Filter by minimum number of adds
    grouped = grouped[grouped["conteo"] >= 10]
    #Save grouped
    grouped.to_csv(GROUPED_DATA / f"grouped_{state_name}.csv", index= False)
    #Normalized features beetween 0 and 1
    normalized = minmax_columns(grouped, 
                            {"precio_m2_mediana": (0,1), #The higher, the better
                             "precio_m2_cv": (1,0), #The lower, the better
                             "edad_dias_promedio": (1,0)}) #The lower, the better
    #Compute score
    normalized = score(normalized)
    #save_scored_data
    normalized.to_csv(SCORED_DATA / f"scored_{state_name}.csv", index= False)

    return normalized

def get_top(data: pd.DataFrame, top:int = 10, criterion: str = "score") -> pd.DataFrame:
    top_data = data.sort_values(by=criterion, ascending=False).head(top)
    return top_data
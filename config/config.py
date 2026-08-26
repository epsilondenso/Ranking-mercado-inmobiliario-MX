columns_to_maintain = ["city", 
                       "neighborhood",
                       "price", 
                       "currency",
                       "built_m2", 
                       "published_date", 
                       "scraped_at"]

columns_not_null = ["neighborhood",
                    "price",
                    "built_m2"]

columns_renamed = ["municipio", 
                   "colonia",
                   "precio",
                   "construidos_m2",
                   "fecha_publi", 
                   "fecha_scrap"]

fecha_scrap = "2026-08-26"
tipo_cambio = 17.04
min_ads = 10

pesos_pavcscore = [0.50, #Price
                   0.25, #Age
                   0.25] #Variation coefficient

#Normalized
columns_score = ["precio_m2_mediana",  #Price
                 "edad_dias_promedio", #Age
                 "precio_m2_cv"]       #Variation coefficient

#-- QS_SCORE (Quality-Strenght) --

#QS
qs_weights = [0.75,
              0.25]

#QUALITY
q_weights = [0.75, #Price
             0.25] #Age
#Normalized
q_columns = ["precio_m2_mediana",  #Price
             "edad_dias_promedio"] #Age

#STRENGHT
s_weights = [1 #ln(1 + Number_of_ads) 
             ]
#Normalized
s_columns = [
             "ln(1+n)"
             ]



paleta = {"oscuro":"#313131",
          "contraste":"#fb012b",
          "principal":"#00c2c7",
          "claro_1":"#ffe28a",
          "claro_2":"#fffeb3"}
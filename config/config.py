columns_to_maintain = ["city", 
                       "neighborhood",
                       "price", 
                       "built_m2", 
                       "published_date"]

columns_not_null = ["neighborhood",
                    "price",
                    "built_m2"]

columns_renamed = ["municipio", 
                   "colonia",
                   "precio",
                   "construidos_m2",
                   "fecha_publi"]

fecha_scrap = "2026-08-12"
pesos_score = [0.50, 0.25, 0.25]
columns_score = ["precio_m2_mediana", "edad_dias_promedio", "precio_m2_cv"]
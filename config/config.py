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

fecha_scrap = "2026-08-14"
pesos_score = [0.50, 0.25, 0.25]
columns_score = ["precio_m2_mediana", "edad_dias_promedio", "precio_m2_cv"]

paleta = {"oscuro":"#313131",
"contraste":"#fb2e01",
"principal":"#6fcb9f",
"claro_1":"#ffe28a",
"claro_2":"#fffeb3"}
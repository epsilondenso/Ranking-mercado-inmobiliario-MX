# Ranking de colonias del mercado inmobiliario en México

Procesa anuncios de inmuebles en venta, resume precio por m², antigüedad y variabilidad por colonia, y genera puntajes para ordenarlas. El resultado final son GeoJSON de códigos postales en los que cada colonia tiene su `score` y su `precio_m2`, listos para pintar un mapa.

## Flujo completo

Ejecuta todos los comandos desde la raíz del repositorio. Los nombres de estado (`<Estado>`) usan CamelCase sin acentos ni espacios (`CDMX`, `EstadodeMexico`, `NuevoLeon`) y coinciden en CSV y GeoJSON.

```text
data/raw/properties_<Estado>.csv
  ├─ 1. src/pipeline.py        → data/{clean,grouped,scored}/*_<Estado>.csv   (ranking por estado)
  ├─ 2. global_norm.py         → data/scored/global_norm.csv                  (ranking global por colonia)
  └─ 3. geocoding/assign_cp.py → data/geocoded/geocoded_<Estado>.csv
        4. global_norm_cp.py   → data/scored/global_norm_cp.csv               (ranking global colonia-CP)
        5. insertar_score_json.py → geojson_with_scores/cp_<Estado>.geojson   (score en cada colonia)
```

### 0. Instalación

```bash
python -m pip install -r requirements.txt
```

Los polígonos de CP van en `geojson_with_names/cp_<Estado>.geojson` (no versionados ).

### 1. Ranking por estado

```python
from src.pipeline import full_treatment, get_top

resultado = full_treatment("data/raw/properties_Sonora.csv")
print(get_top(resultado, top=10, criterion="qs_score")[["municipio", "colonia", "qs_score"]])
```

Para cada estado: limpia los datos, convierte USD a MXN, calcula `precio_m2`, quita atípicos (IQR), calcula la edad del anuncio, agrupa por municipio y colonia, descarta grupos con menos de `min(min_ads, mediana de anuncios)` y normaliza (min-max) **dentro del estado**. Guarda `clean_`, `grouped_` y `scored_<Estado>.csv`. `notebooks/test.ipynb` lo corre para todos los estados y grafica los primeros lugares.

### 2. Ranking global

```bash
python global_norm.py
```

Junta todos los `data/grouped/grouped_*.csv` y normaliza sobre el conjunto nacional, así que los puntajes ya son comparables entre estados. Requiere haber corrido el paso 1. Salida: `data/scored/global_norm.csv`.

### 3. Asignar código postal a cada anuncio

```bash
python -m geocoding.assign_cp
```

Cruza las coordenadas de cada anuncio con los polígonos de CP (*point-in-polygon*). Agrega `codigo_postal` y `cp_metodo`: `within` si cae dentro de un polígono, `nearest` si cae en un hueco y hay un polígono a ≤ `cp_max_distancia_m` (500 m), o vacío en otro caso. Salida: `data/geocoded/geocoded_<Estado>.csv`.

### 4. Ranking global por colonia y CP

```bash
python global_norm_cp.py
```

Hace los mismos pasos de limpieza que el paso 1, pero con los CSV geocodificados. Agrupa por estado, ciudad, municipio (tomado del polígono), colonia y CP, exige al menos `min_ads_cp` (3) anuncios y normaliza a nivel nacional. Salida: `data/scored/global_norm_cp.csv`, con `conteo_cp` (anuncios en esa colonia-CP), `proporcion_cp_colonia` (fracción de los anuncios de la colonia que caen en ese CP), `precio_m2` y los puntajes; es la entrada directa del paso 5.

### 5. Asignar score a cada colonia de los GeoJSON

```bash
python insertar_score_json.py
```

Para cada polígono de `geojson_with_names/`, busca cada colonia de `properties.colonias` en `global_norm_cp.csv` por (CP, nombre normalizado sin acentos ni mayúsculas) y le escribe `score` (= `qs_score`) y `precio_m2` (mediana); si no la encuentra, los deja en `null`. Las colonias con score que no estaban en el GeoJSON se añaden a su CP. Solo usa colonia-CP con `conteo_cp >= MIN_ANUNCIOS` (3, constante en el script). Salida: `geojson_with_scores/cp_<Estado>.geojson`.

## Puntajes

- **PAVC**: mediana de precio/m² (50 %), antigüedad promedio (25 %) y coeficiente de variación (25 %).
- **QS** (el que se usa en el mapa): calidad 75 % (precio 75 %, antigüedad 25 %) + tamaño de mercado 25 % (`ln(1 + n)`).

En antigüedad y variabilidad, menor valor da mayor puntuación. Pesos, `tipo_cambio`, `fecha_scrap`, `min_ads` y `min_ads_cp` están en `config/config.py`; las rutas, en `config/paths.py`.

## Limitaciones

- La normalización del paso 1 es por estado: esos puntajes no se comparan entre estados (usa los pasos 2 o 4).
- `filter_date` solo conserva anuncios publicados después de 2024.
- `tipo_cambio` y `fecha_scrap` son constantes: actualízalas para otro corte de datos.
- El cruce del paso 5 depende de que el nombre de la colonia en los anuncios coincida con el del GeoJSON.

## Estructura

```text
config/                Rutas y parámetros
src/                   Preprocesamiento, limpieza, puntuación, gráficas y pipeline por estado
geocoding/             Asignación de código postal
global_norm.py         Ranking global por colonia
global_norm_cp.py      Ranking global por colonia y CP
insertar_score_json.py Score y precio en los GeoJSON
notebooks/             Ejecución por estados y visualización
data/raw/              Anuncios originales por estado
data/{clean,grouped,scored,geocoded}/  Salidas generadas (CSV no versionados)
geojson_with_names/    Polígonos de CP por estado (no versionado)
geojson_with_scores/   Polígonos de CP con score por colonia
```

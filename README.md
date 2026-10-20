# Ranking de colonias del mercado inmobiliario en México

Procesa anuncios de inmuebles en venta, resume precio por m², antigüedad y variabilidad por colonia, y genera puntajes para ordenarlas. El resultado final son GeoJSON de códigos postales en los que cada colonia tiene su `score` y su `precio_m2`, listos para pintar un mapa.

## Flujo completo

Ejecuta todos los comandos desde la raíz del repositorio. Los nombres de estado (`<Estado>`) usan CamelCase sin acentos ni espacios (`CDMX`, `EstadodeMexico`, `NuevoLeon`) y coinciden en CSV y GeoJSON.

```text
data/raw/properties_<Estado>.csv
  ├─ 1. src/pipeline.py        → data/{clean,grouped,scored}/*_<Estado>.csv   (ranking por estado)
  ├─ 2. global_norm.py         → data/scored/global_norm.csv                  (ranking global por colonia)
  └─ 3. geocoding/assign_cp.py → data/geocoded/geocoded_<Estado>.csv
        4. global_norm_cp.py   → data/scored/global_norm_cp.csv               (ranking global por colonia, en su CP principal)
        5. insertar_score_json.py → geojson_with_scores/cp_<Estado>.geojson   (score en cada colonia y precio por CP)
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

Para cada estado: limpia los datos, convierte USD a MXN, calcula `precio_m2`, quita atípicos (IQR), calcula la edad del anuncio, agrupa por municipio y colonia, descarta colonias con menos de `min_ads` (3) anuncios y normaliza (min-max) **dentro del estado**. Guarda `clean_`, `grouped_` y `scored_<Estado>.csv`. `notebooks/test.ipynb` lo corre para todos los estados y grafica los primeros lugares.

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

Hace los mismos pasos de limpieza que el paso 1, pero con los CSV geocodificados, y normaliza a nivel nacional.

- **Métricas por colonia.** Agrupa por estado, ciudad y colonia con *todos* los anuncios de la colonia, sin partirla por CP; los anuncios sin CP también cuentan. Exige al menos `min_ads_cp` (3) anuncios en la colonia. Con `min_ads = min_ads_cp`, el conjunto de colonias, su conteo y su mediana de precio son los mismos que en el paso 1 (solo cambia la normalización).
- **CP principal.** Un CP puede contener varias colonias y una colonia puede repartir sus anuncios entre varios CP (bordes del polígono o errores de geocodificación). Cada colonia se ubica en un solo CP: el que concentra más de sus anuncios (en empate, el de menor número). El municipio se toma del polígono de ese CP. Las colonias sin ningún anuncio con CP se descartan porque no se pueden ubicar en el mapa.

Salida: `data/scored/global_norm_cp.csv`, una fila por colonia, con `codigo_postal` (CP principal), `conteo` (anuncios de la colonia), `conteo_cp` (anuncios que caen en el CP principal), `proporcion_cp_colonia` (`conteo_cp / anuncios con CP`), `precio_m2` (mediana de la colonia) y los puntajes; es la entrada directa del paso 5.

### 5. Asignar score a cada colonia de los GeoJSON

```bash
python insertar_score_json.py
```

Para cada polígono de `geojson_with_names/`, busca cada colonia de `properties.colonias` en `global_norm_cp.csv` por (CP, nombre normalizado sin acentos ni mayúsculas) y le escribe `score` (= `qs_score`), `precio_m2` (mediana de la colonia) y `conteo` (anuncios); si no la encuentra, los deja en `null`. Las colonias con score que no estaban en el GeoJSON se añaden a su CP principal. Solo usa colonias con `conteo >= min_ads_cp`. Dos casos de duplicados:

- Si en los anuncios la misma colonia aparece con dos ciudades distintas y comparte CP principal (p. ej. "Puerto Morelos" como Cancún y como Puerto Morelos), se fusiona en una sola: suma los anuncios y pondera `precio_m2` y `score` por anuncios.
- Si el GeoJSON repite un nombre en el mismo CP con distinto `tipo_asenta` (p. ej. "San Marcos" Colonia y Barrio), los datos se escriben solo en la primera aparición, para no contar la colonia dos veces en el polígono. Salida: `geojson_with_scores/cp_<Estado>.geojson` (estructura indentada; cada geometría y cada colonia en una sola línea para no inflar el tamaño). `--decimales N` redondea las coordenadas; por defecto conserva la precisión original.

Estructura de cada feature, pensada para el mapa:

```json
{"type": "Feature", "properties": {
  "d_codigo": "20358", "estado": "...", "municipio": "...",
  "score_cp": 0.2377, "precio_m2_cp": 20960.0, "n_colonias_score": 2,
  "colonias": [{"colonia": "Monteverde", "tipo_asenta": "Fraccionamiento", "conteo": null, "precio_m2": null, "score": null}]
}, "geometry": {...}}
```

- `d_codigo`: CP como texto de cinco dígitos.
- `precio_m2_cp`: media de `precio_m2` de las colonias del CP **ponderada por su `conteo`**, de modo que una colonia con 40 anuncios pesa más que una con 3. Es el valor para colorear el polígono.
- `score_cp`: media de `score` de las colonias del CP, también ponderada por `conteo`.
- `n_colonias_score`: número de colonias con score en el CP.
- `colonias`: detalle por colonia para tooltips. `tipo_asenta` es `null` en las colonias añadidas desde los anuncios; `conteo`, `precio_m2` y `score` son `null` en las colonias sin datos. Cada colonia con datos aparece solo en su CP principal.

## Puntajes

- **PAVC**: mediana de precio/m² (50 %), antigüedad promedio (25 %) y coeficiente de variación (25 %).
- **QS** (el que se usa en el mapa): calidad 75 % (precio 75 %, antigüedad 25 %) + tamaño de mercado 25 % (`ln(1 + n)`).

En antigüedad y variabilidad, menor valor da mayor puntuación. Pesos, `tipo_cambio`, `fecha_scrap`, `min_ads` y `min_ads_cp` están en `config/config.py`; las rutas, en `config/paths.py`.

## Limitaciones

- La normalización del paso 1 es por estado: esos puntajes no se comparan entre estados (usa los pasos 2 o 4).
- `filter_date` solo conserva anuncios publicados después de 2024.
- `tipo_cambio` y `fecha_scrap` son constantes: actualízalas para otro corte de datos.
- El cruce del paso 5 depende de que el nombre de la colonia en los anuncios coincida con el del GeoJSON.
- Una colonia que de verdad abarca varios CP solo colorea su CP principal; los demás CP no reciben su precio aunque tengan algunos de sus anuncios.

## Estructura

```text
config/                Rutas y parámetros
src/                   Preprocesamiento, limpieza, puntuación, gráficas y pipeline por estado
geocoding/             Asignación de código postal
global_norm.py         Ranking global por colonia
global_norm_cp.py      Ranking global por colonia, ubicada en su CP principal
insertar_score_json.py Score y precio en los GeoJSON
notebooks/             Ejecución por estados y visualización
data/raw/              Anuncios originales por estado
data/{clean,grouped,scored,geocoded}/  Salidas generadas (CSV no versionados)
geojson_with_names/    Polígonos de CP por estado (no versionado)
geojson_with_scores/   Polígonos de CP con score por colonia
```
